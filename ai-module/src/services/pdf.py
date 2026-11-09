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
from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_PDF_BYTES = 10 * 1024 * 1024
READ_SIZE = 64 * 1024
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
# 페이지 수 상한. 악성 PDF가 전체 파싱으로 시간·메모리를 점유하는 것을 1차로 막는다.
# 텍스트를 읽기 전에 페이지 수부터 확인해 초과하면 거부한다(DB 설계서 4장, API 설계서 6.1).
MAX_PAGES = 500


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


def check_page_count(path: Path) -> None:
    """전체 텍스트를 읽기 전에 페이지 수만 확인하고, 500쪽 초과면 거부한다.

    PyPDFLoader로 본문을 추출하기 전에 호출한다. 읽을 수 없는 PDF(손상·암호화 등
    PyPdfError)는 extract_chunks와 같은 정책으로 TEXT_EXTRACTION_FAILED(422)로 매핑한다.
    디스크·스트림 오류나 예상치 못한 버그(PyPdfError가 아닌 예외)는 422로 감추지 않고
    그대로 전파한다. 페이지 수 세기도 CPU/메모리를 쓸 수 있으나 전량 파싱보다는 가볍다.
    """
    try:
        page_count = len(PdfReader(str(path)).pages)
    except PyPdfError:
        raise PdfProcessingError("TEXT_EXTRACTION_FAILED", 422) from None
    if page_count > MAX_PAGES:
        raise PdfProcessingError("TOO_MANY_PAGES", 422)


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
        # 본문 추출 전에 페이지 수부터 확인해 상한 초과 PDF를 먼저 거부한다.
        check_page_count(path)
        return extract_chunks(
            path, owner_uuid=owner_uuid, document_id=document_id,
            document_name=document_name,
        )
