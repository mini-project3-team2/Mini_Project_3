"""Prepare validated embedding vectors in memory. No vector-store access."""

import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from numbers import Real
from typing import Protocol

from langchain_core.documents import Document
from openai import OpenAIError

from src.services.pdf import CHUNK_SIZE

BATCH_SIZE = 64
VECTOR_DIMENSIONS = 1536
MAX_INPUT_TOKEN_BOUND = 8191
MAX_BATCH_TOKEN_BOUND = 300_000
REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_BUDGET_SECONDS = 100.0


class EmbeddingClient(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingPreparationError(Exception):
    """Safe error for the future HTTP adapter; never includes provider text."""

    def __init__(self, code: str, status_code: int = 503):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class EmbeddedChunk:
    # repr deliberately excludes document text, metadata, and vector contents.
    text: str = field(repr=False)
    metadata: dict[str, str | int] = field(repr=False)
    vector: tuple[float, ...] = field(repr=False)


def _snapshot(chunks: Sequence[Document]) -> list[Document]:
    """Validate all inputs before paying for any request; copy scalar metadata.

    For this byte-level BPE model, UTF-8 bytes are a conservative upper bound,
    not a measured token count. C2's 800-character limit gives <=3200 bytes per
    chunk and <=204800 per 64-item batch, without downloading a tokenizer.
    """
    if not chunks:
        raise EmbeddingPreparationError("INVALID_INPUT", 400)
    snapshot = []
    for chunk in chunks:
        text = chunk.page_content
        try:
            bound = len(text.encode("utf-8"))
        except UnicodeEncodeError:
            raise EmbeddingPreparationError("INVALID_INPUT", 400) from None
        if not text.strip() or len(text) > CHUNK_SIZE or bound > MAX_INPUT_TOKEN_BOUND:
            raise EmbeddingPreparationError("INVALID_INPUT", 400)
        metadata = chunk.metadata
        if (
            set(metadata) != {"owner_uuid", "document_id", "document_name", "page"}
            or not isinstance(metadata["owner_uuid"], str)
            or not metadata["owner_uuid"].strip()
            or not isinstance(metadata["document_name"], str)
            or not metadata["document_name"].strip()
            or type(metadata["document_id"]) is not int
            or metadata["document_id"] <= 0
            or type(metadata["page"]) is not int
            or metadata["page"] <= 0
        ):
            raise EmbeddingPreparationError("INVALID_INPUT", 400)
        snapshot.append(Document(page_content=text, metadata=dict(metadata)))
    return snapshot


def _validate_vectors(raw: list[list[float]], count: int) -> list[tuple[float, ...]]:
    if not isinstance(raw, (list, tuple)) or len(raw) != count:
        raise EmbeddingPreparationError("EMBEDDING_ERROR")
    vectors = []
    for row in raw:
        if not isinstance(row, (list, tuple)) or len(row) != VECTOR_DIMENSIONS:
            raise EmbeddingPreparationError("EMBEDDING_ERROR")
        vector = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, Real):
                raise EmbeddingPreparationError("EMBEDDING_ERROR")
            try:
                number = float(value)
            except (ValueError, OverflowError):
                raise EmbeddingPreparationError("EMBEDDING_ERROR") from None
            if not math.isfinite(number):
                raise EmbeddingPreparationError("EMBEDDING_ERROR")
            vector.append(number)
        if not any(vector):
            raise EmbeddingPreparationError("EMBEDDING_ERROR")
        vectors.append(tuple(vector))
    return vectors


async def embed_chunks(
    chunks: Sequence[Document], client: EmbeddingClient,
    *, budget_seconds: float = DEFAULT_BUDGET_SECONDS,
) -> list[EmbeddedChunk]:
    """Embed C2 chunks with the shared client; return only after all batches pass.

    Caller supplies the remaining ingestion budget (PDF time already deducted).
    No retries, persistence, collection creation, or partial result delivery.
    The injected production client must also have SDK retries disabled.
    Cancellation propagates rather than becoming an application error.
    """
    loop = asyncio.get_running_loop()
    if not math.isfinite(budget_seconds) or budget_seconds < 0:
        raise ValueError("budget_seconds must be finite and non-negative")
    deadline = loop.time() + budget_seconds
    snapshot = _snapshot(chunks)
    result = []
    for start in range(0, len(snapshot), BATCH_SIZE):
        batch = snapshot[start:start + BATCH_SIZE]
        texts = [chunk.page_content for chunk in batch]
        if sum(len(text.encode("utf-8")) for text in texts) > MAX_BATCH_TOKEN_BOUND:
            raise EmbeddingPreparationError("INVALID_INPUT", 400)
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise EmbeddingPreparationError("INGESTION_TIMEOUT")
        try:
            async with asyncio.timeout(min(REQUEST_TIMEOUT_SECONDS, remaining)):
                raw = await client.aembed_documents(texts)
        except TimeoutError:
            code = "INGESTION_TIMEOUT" if loop.time() >= deadline else "EMBEDDING_ERROR"
            raise EmbeddingPreparationError(code) from None
        except OpenAIError:
            code = "INGESTION_TIMEOUT" if loop.time() >= deadline else "EMBEDDING_ERROR"
            raise EmbeddingPreparationError(code) from None
        vectors = _validate_vectors(raw, len(batch))
        if loop.time() >= deadline:
            raise EmbeddingPreparationError("INGESTION_TIMEOUT")
        result.extend(
            EmbeddedChunk(chunk.page_content, dict(chunk.metadata), vector)
            for chunk, vector in zip(batch, vectors, strict=True)
        )
    return result
