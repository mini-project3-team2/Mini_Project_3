"""Persistent collection with no implicit embedding provider."""

import asyncio
import logging
from contextlib import asynccontextmanager

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.types import Documents, EmbeddingFunction
from chromadb.utils.embedding_functions import register_embedding_function

from src.core.config import Settings


@register_embedding_function
class ExplicitVectorsOnly(EmbeddingFunction[Documents]):
    """Prevent Chroma's schema defaults from silently selecting another model."""

    def __init__(self):
        pass

    def __call__(self, input):
        raise ValueError("Explicit embeddings or query_embeddings are required")

    @staticmethod
    def name():
        return "asknote_explicit_vectors_only"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return ExplicitVectorsOnly()


@asynccontextmanager
async def open_collection(settings: Settings):
    # Initialization/close can touch SQLite; keep them off the event loop.
    client = await asyncio.to_thread(
        chromadb.PersistentClient,
        path=str(settings.chroma_persist_directory),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        collection = await asyncio.to_thread(
            client.get_or_create_collection,
            name=settings.collection_name,
            embedding_function=ExplicitVectorsOnly(),
        )
        yield collection
    finally:
        await asyncio.to_thread(client.close)


# --- 질의(LLM 2) 소유자 필터 검색 ---------------------------------------------
# 아래는 질의 경로 전용으로 추가한 코드다. 위의 ExplicitVectorsOnly·open_collection과
# 그 동작은 바꾸지 않는다. Chroma는 query_embeddings를 명시적으로 받아야 하므로
# (ExplicitVectorsOnly가 자동 임베딩을 거부함) 질문 벡터를 직접 넘긴다.

from dataclasses import dataclass  # noqa: E402

logger = logging.getLogger(__name__)

# 검색 기본 k. DB 설계서 4장 기준(similarity, k=4). 코드 상수로 둔다.
DEFAULT_K = 4

# 관련도 필터 임시 임계값. 컬렉션 거리 함수는 Chroma 기본 L2(제곱 유클리드)이고,
# 임베딩이 정규화 단위 벡터라 실질 범위는 0~2다(L2² = 2 - 2·cos, 유사도 0.5 ≈ 1.0).
# "거리 <= MAX_DISTANCE"만 남긴다(작을수록 유사). 로그로 실제 점수를 보고 한 곳에서 조정한다.
MAX_DISTANCE = 1.0

# 검색 결과 점수 로그 레벨. 기준값을 정한 뒤 logging.DEBUG로 낮출 수 있게 한 곳에 둔다.
SEARCH_LOG_LEVEL = logging.INFO


class SearchError(Exception):
    """검색 단계 실패. SSE error의 SEARCH_ERROR로 매핑된다(원문·값은 담지 않음)."""


@dataclass(frozen=True)
class SearchHit:
    """검색 결과 한 건. 출처는 LLM이 아니라 이 메타데이터로 만든다.

    distance는 컬렉션의 거리(L2²). 작을수록 질문과 유사하다. 관련도 필터에 쓴다.
    """
    document_id: int
    document_name: str
    page: int
    text: str
    distance: float


def owner_document_filter(owner_uuid: str, document_ids: list[int]) -> dict:
    """owner_uuid AND document_id $in 조건. 두 조건으로만 사용자·문서를 격리한다."""
    return {
        "$and": [
            {"owner_uuid": owner_uuid},
            {"document_id": {"$in": list(document_ids)}},
        ]
    }


def _to_hits(result: dict) -> list[SearchHit]:
    """Chroma query 응답(단일 질의)에서 검색 순서를 유지해 SearchHit로 변환한다."""
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    hits: list[SearchHit] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        hits.append(
            SearchHit(
                document_id=int(metadata["document_id"]),
                document_name=str(metadata["document_name"]),
                page=int(metadata["page"]),
                text=str(text),
                distance=float(distance),
            )
        )
    return hits


async def search(
    collection,
    query_embedding: list[float],
    *,
    owner_uuid: str,
    document_ids: list[int],
    k: int = DEFAULT_K,
) -> list[SearchHit]:
    """소유자 필터 유사도 검색. 결과를 검색 순서 그대로(중복 제거 없이) 반환한다.

    document_ids가 비면 검색을 생략하고 빈 리스트를 반환한다(방어적 처리 —
    스키마에서 빈 배열은 이미 400으로 막힌다). 동기 Chroma 호출은 작업 스레드로
    실행해 이벤트 루프를 막지 않는다. 호출자는 query_embedding을 명시적으로 넘긴다.
    """
    if not document_ids:
        return []
    where = owner_document_filter(owner_uuid, document_ids)
    try:
        result = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        # 원인 원문을 숨기고 검색 실패로만 분류한다.
        raise SearchError("SEARCH_ERROR") from None
    hits = _to_hits(result)
    # 관련도 기준값을 정하기 위한 점수 로그. 필터 전 전체 결과의 식별자·거리만 남기고,
    # 청크 본문·질문 내용은 남기지 않는다. 기준 확정 후 SEARCH_LOG_LEVEL을 DEBUG로 낮춘다.
    if logger.isEnabledFor(SEARCH_LOG_LEVEL):
        for hit in hits:
            logger.log(
                SEARCH_LOG_LEVEL,
                "query_search_result doc_id=%s page=%s distance=%.4f",
                hit.document_id, hit.page, hit.distance,
            )
    return hits


def filter_by_distance(hits: list[SearchHit], max_distance: float = MAX_DISTANCE) -> list[SearchHit]:
    """거리가 기준보다 큰(덜 관련된) 조각을 버린다. 순서는 유지한다.

    라우터가 search 직후 한 번 호출해, 걸러진 결과를 sources와 LLM 근거 자료 양쪽에
    똑같이 넘긴다. 전부 걸러지면 빈 리스트가 되어 기존 0건 처리(거절 문구)가 그대로 돈다.
    소유자 격리(search의 where)와는 분리된 단계다.
    """
    return [hit for hit in hits if hit.distance <= max_distance]


def dedupe_sources(hits: list[SearchHit]) -> list[dict]:
    """sources 이벤트용 출처 목록. (documentId, page)가 같으면 하나로 합치고 순서는 유지.

    같은 페이지의 청크가 여러 개 검색돼도 화면 출처 카드는 한 번만 뜨게 한다.
    페이지가 다르면 각각 남긴다(mock-data/internal/query-stream-success.txt와 동일).
    프롬프트 근거 자료에는 hits를 전부(합치지 않고) 쓰고, 합치기는 여기서만 한다.
    """
    seen: set[tuple[int, int]] = set()
    sources: list[dict] = []
    for hit in hits:
        key = (hit.document_id, hit.page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "documentId": hit.document_id,
                "documentName": hit.document_name,
                "page": hit.page,
            }
        )
    return sources
