"""Single-process ingestion coordinator: validated chunks -> embeddings -> Chroma.

Use ONE coordinator per application. No HTTP or DELETE endpoint lives here.
Synchronous storage work owns rollback and is drained before releasing its guard.
"""

import asyncio
import logging
import math
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from uuid import UUID

from langchain_core.documents import Document

from src.services.embedding import DEFAULT_BUDGET_SECONDS, embed_chunks

logger = logging.getLogger(__name__)
STORE_BATCH_SIZE = 64


class IngestionError(Exception):
    def __init__(self, code: str, status_code: int = 503):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class IngestionResult:
    document_id: int
    chunk_count: int


def document_filter(owner_uuid, document_id):
    return {"$and": [{"owner_uuid": owner_uuid}, {"document_id": document_id}]}


def _existing(collection, where):
    try:
        return collection.get(where=where, limit=1, include=[])["ids"]
    except Exception:
        raise IngestionError("STORAGE_ERROR") from None


def delete_document_chunks(collection, owner_uuid, document_id):
    where = document_filter(owner_uuid, document_id)
    collection.delete(where=where)
    if _existing(collection, where):
        raise IngestionError("STORAGE_ERROR")


def _cleanup(collection, ids, where):
    """Delete only attempted IDs within this owner/document, and verify removal."""
    try:
        for start in range(0, len(ids), STORE_BATCH_SIZE):
            batch = ids[start:start + STORE_BATCH_SIZE]
            collection.delete(ids=batch, where=where)
            if collection.get(ids=batch, where=where, include=[])["ids"]:
                raise IngestionError("STORAGE_ERROR")
    except Exception:
        logger.error("ingestion_cleanup_failed")
        raise IngestionError("STORAGE_ERROR") from None


def _check_budget(deadline, cancelled):
    if cancelled.is_set() or time.monotonic() >= deadline:
        raise IngestionError("INGESTION_TIMEOUT")


def _store(collection, chunks, ids, where, deadline, cancelled):
    attempted = []
    try:
        _check_budget(deadline, cancelled)
        # Defensive recheck. Atomicity still requires the single-process guard.
        if _existing(collection, where):
            raise IngestionError("DOCUMENT_ALREADY_EXISTS", 409)
        for start in range(0, len(chunks), STORE_BATCH_SIZE):
            _check_budget(deadline, cancelled)
            batch = chunks[start:start + STORE_BATCH_SIZE]
            batch_ids = ids[start:start + STORE_BATCH_SIZE]
            attempted.extend(batch_ids)  # add can partially persist before raising
            collection.add(
                ids=batch_ids,
                documents=[chunk.text for chunk in batch],
                embeddings=[list(chunk.vector) for chunk in batch],
                metadatas=[dict(chunk.metadata) for chunk in batch],
            )
        _check_budget(deadline, cancelled)
        actual = collection.get(where=where, include=[])["ids"]
        if len(actual) != len(ids) or set(actual) != set(ids):
            raise IngestionError("STORAGE_ERROR")
        _check_budget(deadline, cancelled)
    except BaseException as error:
        if attempted:
            _cleanup(collection, attempted, where)
        if isinstance(error, IngestionError):
            raise
        if isinstance(error, Exception):
            raise IngestionError("STORAGE_ERROR") from None
        raise


async def _drain(task):
    """Repeated caller cancellation must not release the document guard early."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


@dataclass
class _DocumentState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0
    uploader: asyncio.Task | None = None


class IngestionCoordinator:
    def __init__(self):
        self._documents = {}

    @asynccontextmanager
    async def document_operation(self, owner_uuid, document_id, *, deleting=False):
        """One application event loop. Deletes queue, competing uploads receive 409."""
        key = (owner_uuid, document_id)
        state = self._documents.get(key)
        task = asyncio.current_task()
        if state is None:
            state = self._documents[key] = _DocumentState()
        elif not deleting:
            if state.uploader is not task:
                raise IngestionError("INGESTION_IN_PROGRESS", 409)
            # The HTTP handler already reserved this document before PDF preparation.
            yield
            return

        state.users += 1
        try:
            async with state.lock:
                if not deleting:
                    state.uploader = task
                try:
                    yield
                finally:
                    state.uploader = None
        finally:
            state.users -= 1
            if not state.users:
                del self._documents[key]

    async def ingest(self, chunks, embeddings, collection,
                     *, budget_seconds=DEFAULT_BUDGET_SECONDS):
        """Caller passes C2 chunks, shared clients, and remaining time budget.

        No retries or upsert. Same owner/document is rejected while active.
        Blocking Chroma calls cannot be force-cancelled: timeout/cancellation
        waits for the worker and rollback, so this is not a hard HTTP deadline.
        """
        if not math.isfinite(budget_seconds) or budget_seconds < 0:
            raise ValueError("budget_seconds must be finite and non-negative")
        deadline = time.monotonic() + budget_seconds
        if not chunks:
            raise IngestionError("INVALID_INPUT", 400)
        try:
            metadata = chunks[0].metadata
            owner = str(UUID(metadata["owner_uuid"]))
            if metadata["owner_uuid"].lower() != owner:
                raise ValueError()
            doc_id = metadata["document_id"]
            name = metadata["document_name"]
            if type(doc_id) is not int or not 0 < doc_id <= 9223372036854775807:
                raise ValueError()
            snapshot = []
            for chunk in chunks:
                if (str(UUID(chunk.metadata["owner_uuid"])) != owner
                        or chunk.metadata["document_id"] != doc_id
                        or chunk.metadata["document_name"] != name):
                    raise ValueError()
                snapshot.append(Document(page_content=chunk.page_content,
                                         metadata=chunk.metadata | {"owner_uuid": owner}))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise IngestionError("INVALID_INPUT", 400) from None
        where = document_filter(owner, doc_id)
        cancelled = threading.Event()
        async with self.document_operation(owner, doc_id):
            _check_budget(deadline, cancelled)
            check = asyncio.create_task(asyncio.to_thread(_existing, collection, where))
            try:
                exists = await asyncio.shield(check)
            except asyncio.CancelledError:
                await _drain(check)
                raise
            if exists:
                raise IngestionError("DOCUMENT_ALREADY_EXISTS", 409)
            _check_budget(deadline, cancelled)
            prepared = await embed_chunks(snapshot, embeddings,
                                          budget_seconds=max(0, deadline - time.monotonic()))
            ids = [f"{owner}:{doc_id}:{index}" for index in range(len(prepared))]
            worker = asyncio.create_task(asyncio.to_thread(
                _store, collection, prepared, ids, where, deadline, cancelled
            ))
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                cancelled.set()
                try:
                    await _drain(worker)
                except IngestionError as error:
                    if error.code != "INGESTION_TIMEOUT":
                        raise
                else:
                    # Cancellation raced with a successful write: undo it while
                    # this request still exclusively owns its document guard.
                    cleanup = asyncio.create_task(asyncio.to_thread(_cleanup, collection, ids, where))
                    await _drain(cleanup)
                raise
            return IngestionResult(doc_id, len(prepared))
