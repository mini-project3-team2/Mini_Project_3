"""Authenticated internal PDF ingestion and document deletion."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from src.core.security import require_internal_token
from src.schemas.documents import IngestInput, IngestResponse, parse_document_identity
from src.services.embedding import EmbeddingPreparationError, DEFAULT_BUDGET_SECONDS
from src.services.ingest import IngestionError, delete_document_chunks
from src.services.pdf import PdfProcessingError, prepare_pdf

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_internal_token)])
MAX_MULTIPART_BYTES = 11 * 1024 * 1024


async def finish_before_cancelling(awaitable):
    """Do not close UploadFile/resources while their worker is still using them."""
    task = asyncio.create_task(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Retrieve the exception without echoing details or replacing cancellation.
        if not task.cancelled():
            task.exception()
        raise


@router.post(
    "/internal/documents", response_model=IngestResponse,
    responses={code: {"description": description} for code, description in {
        400: "INVALID_INPUT / EMPTY_FILE / INVALID_FILE_TYPE",
        401: "Unauthorized", 409: "DOCUMENT_ALREADY_EXISTS / INGESTION_IN_PROGRESS",
        413: "FILE_TOO_LARGE", 422: "TEXT_EXTRACTION_FAILED",
        500: "INTERNAL_ERROR", 503: "EMBEDDING_ERROR / STORAGE_ERROR / INGESTION_TIMEOUT",
    }.items()},
    openapi_extra={"requestBody": {"required": True, "content": {
        "multipart/form-data": {"schema": {
            "type": "object", "required": ["file", "documentId", "ownerUuid", "documentName"],
            "properties": {"file": {"type": "string", "format": "binary"},
                           "documentId": {"type": "integer", "minimum": 1, "maximum": 9223372036854775807},
                           "ownerUuid": {"type": "string", "format": "uuid"},
                           "documentName": {"type": "string", "maxLength": 255}},
        }}
    }}},
)
async def ingest_document(request: Request):
    try:
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
            raise IngestionError("INVALID_INPUT", 400)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await request.receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_MULTIPART_BYTES:
                    raise PdfProcessingError("FILE_TOO_LARGE", 413)
            return message

        form_request = Request(request.scope, receive=limited_receive)
        async with form_request.form(max_files=1, max_fields=16, max_part_size=1024) as form:
            data = IngestInput.from_form(form)
            resources = request.app.state.resources
            async with resources.ingestion.document_operation(data.owner_uuid, data.document_id):
                return await _ingest_pdf(data, resources)
    except (IngestionError, PdfProcessingError, EmbeddingPreparationError) as error:
        return JSONResponse(status_code=error.status_code, content={"error": error.code})
    except HTTPException as error:
        # Multipart parser errors must not echo input or use PDF extraction 422.
        if error.status_code == 400:
            return JSONResponse(status_code=400, content={"error": "INVALID_INPUT"})
        raise
    except Exception:
        logger.error("document_ingestion_internal_error")
        return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR"})


async def _ingest_pdf(data, resources):
    deadline = time.monotonic() + DEFAULT_BUDGET_SECONDS
    chunks = await finish_before_cancelling(asyncio.to_thread(
        prepare_pdf, data.file.file, data.file.filename,
        owner_uuid=data.owner_uuid, document_id=data.document_id,
        document_name=data.document_name,
    ))

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise IngestionError("INGESTION_TIMEOUT")
        return seconds

    remaining()
    try:
        collection = await finish_before_cancelling(resources.collection())
    except Exception:
        raise IngestionError("STORAGE_ERROR") from None
    remaining()
    try:
        embeddings = await finish_before_cancelling(resources.embeddings())
    except Exception:
        raise EmbeddingPreparationError("EMBEDDING_ERROR") from None
    result = await resources.ingestion.ingest(
        chunks, embeddings, collection, budget_seconds=remaining()
    )
    return IngestResponse(documentId=result.document_id, chunkCount=result.chunk_count)


@router.delete(
    "/internal/documents/{documentId}", status_code=204, response_class=Response,
    responses={400: {"description": "INVALID_INPUT"}, 401: {"description": "Unauthorized"},
               503: {"description": "STORAGE_ERROR"}},
    openapi_extra={"parameters": [{"name": "ownerUuid", "in": "query", "required": True,
                                  "schema": {"type": "string", "format": "uuid"}}]},
)
async def delete_document(documentId: str, request: Request):
    owners = request.query_params.getlist("ownerUuid")
    try:
        if len(owners) != 1:
            raise IngestionError("INVALID_INPUT", 400)
        doc_id, owner = parse_document_identity(documentId, owners[0])
    except IngestionError as error:
        return JSONResponse(status_code=error.status_code, content={"error": error.code})

    resources = request.app.state.resources

    async def remove_chunks():
        async with resources.ingestion.document_operation(owner, doc_id, deleting=True):
            collection = await resources.collection()
            await asyncio.to_thread(delete_document_chunks, collection, owner, doc_id)

    try:
        await finish_before_cancelling(remove_chunks())
    except Exception:
        logger.error("document_delete_storage_error")
        return JSONResponse(status_code=503, content={"error": "STORAGE_ERROR"})
    return Response(status_code=204)
