"""Local PDF preparation; call synchronous functions in a worker, not the event loop.

The worker must own the staging context until extraction finishes. Cancelling an
async waiter does not stop its worker and must not remove the worker's file.
No settings, network clients, OCR, or vector stores are accessed here.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf.errors import PyPdfError

MAX_PDF_BYTES = 10 * 1024 * 1024
READ_SIZE = 64 * 1024
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class PdfProcessingError(Exception):
    """Safe domain error; HTTP mapping belongs to the documents router."""

    def __init__(self, code: str, status_code: int):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@contextmanager
def staged_pdf(
    source: BinaryIO, filename: str | None, *, temp_directory: Path | None = None
) -> Iterator[Path]:
    """Copy from the current stream position, enforce size, and always clean up.

    The caller owns the source stream. Neither supplied filename nor metadata
    determines a disk path. temp_directory is for controlled storage/tests only.
    Disk and stream I/O errors propagate as internal errors, never as PDF 422.
    """
    if not filename or not filename.lower().endswith(".pdf"):
        raise PdfProcessingError("INVALID_FILE_TYPE", 400)
    with TemporaryDirectory(prefix="asknote-pdf-", dir=temp_directory) as directory:
        path = Path(directory) / "input.pdf"
        size = 0
        signature = bytearray()
        with path.open("wb") as destination:
            while True:
                block = source.read(min(READ_SIZE, MAX_PDF_BYTES - size + 1))
                if not block:
                    break
                size += len(block)
                if size > MAX_PDF_BYTES:
                    raise PdfProcessingError("FILE_TOO_LARGE", 413)
                if len(signature) < 5:
                    signature.extend(block[: 5 - len(signature)])
                destination.write(block)
        if size == 0:
            raise PdfProcessingError("EMPTY_FILE", 400)
        if signature != b"%PDF-":
            raise PdfProcessingError("INVALID_FILE_TYPE", 400)
        yield path


def extract_chunks(
    path: Path, *, owner_uuid: str, document_id: int, document_name: str
) -> list[Document]:
    """Extract a staged local PDF using already-validated document identity.

    Blank pages do not renumber subsequent pages. Only the four public metadata
    fields survive; loader paths and PDF author metadata are discarded.
    The byte limit does not bound decompressed PDF memory or parser runtime.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = []
    # Catch known PDF interpretation failures only. I/O and programming failures
    # must not be mislabeled as unreadable user documents.
    try:
        pages = PyPDFLoader(str(path), mode="page", extract_images=False).lazy_load()
        for page in pages:
            if not page.page_content.strip():
                continue
            metadata = {
                "owner_uuid": owner_uuid,
                "document_id": document_id,
                "document_name": document_name,
                "page": page.metadata["page"] + 1,
            }
            chunks.extend(
                Document(page_content=text, metadata=dict(metadata))
                for text in splitter.split_text(page.page_content)
                if text.strip()
            )
    except PyPdfError:
        raise PdfProcessingError("TEXT_EXTRACTION_FAILED", 422) from None
    if not chunks:
        raise PdfProcessingError("TEXT_EXTRACTION_FAILED", 422)
    return chunks


def prepare_pdf(
    source: BinaryIO,
    filename: str | None,
    *,
    owner_uuid: str,
    document_id: int,
    document_name: str,
    temp_directory: Path | None = None,
) -> list[Document]:
    """Worker entry point owning both temporary-file and parser lifetimes.

    The caller must keep source open until this function finishes, including
    when an async request is cancelled. Internal auth/identity validation and
    duplicate checks are responsibilities of the future ingestion service.
    """
    with staged_pdf(source, filename, temp_directory=temp_directory) as path:
        return extract_chunks(
            path, owner_uuid=owner_uuid, document_id=document_id,
            document_name=document_name,
        )
