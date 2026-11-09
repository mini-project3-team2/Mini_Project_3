"""소유자 필터 검색 → 답변 스트리밍(SSE). 오류는 이 엔드포인트 안에서 처리한다.

처리 순서(합의): 내부 토큰 인증(의존성) → JSON 파싱 → 필드 검증 → SSE 시작.
토큰이 없으면 본문 상태와 무관하게 401이 먼저 난다.

SSE 규약(API 설계서 6.3):
- 정상: sources → token(반복) → done({})
- 임베딩·검색 오류는 sources 없이 error만 나갈 수 있다(EMBEDDING_ERROR/SEARCH_ERROR).
- 토큰 스트리밍 중 LLM 오류는 sources·일부 token 뒤에 error(LLM_ERROR).
- error data는 코드만. 실제 원인은 서버 로그에만 남기고 키·본문 전체는 남기지 않는다.
클라이언트가 끊으면 LLM 스트리밍을 즉시 멈추고 error 없이 조용히 종료한다(토큰 비용 방어).
"""

import asyncio
import json
import logging
from contextlib import aclosing

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.responses import JSONResponse, StreamingResponse

from src.chains.rag_chain import NO_CONTEXT_MESSAGE, astream_tokens
from src.core.llm import build_llm
from src.core.security import require_internal_token
from src.schemas.query import QueryInputError, QueryRequest
from src.services.embedding import EmbeddingPreparationError
from src.services.vectorstore import SearchError, dedupe_sources, filter_by_distance, search

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_internal_token)])


def _sse(event: str, data) -> bytes:
    """SSE 한 이벤트를 바이트로 만든다. data JSON은 공백 없이 압축, 한글은 그대로 둔다."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


async def _event_stream(request: Request, query: QueryRequest):
    """SSE 본문 생성기. 인증·입력 검증을 통과한 뒤에만 호출된다."""
    resources = request.app.state.resources
    settings = request.app.state.settings

    # 1) 질문 임베딩 — 실패하면 sources 전이므로 error만 나간다.
    try:
        embeddings = await resources.embeddings()
        query_vector = await embeddings.aembed_query(query.question)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("query_stream_failed stage=embedding code=EMBEDDING_ERROR")
        yield _sse("error", {"code": "EMBEDDING_ERROR"})
        return

    # 2) 소유자 필터 검색 — 실패하면 역시 sources 없이 error만.
    try:
        collection = await resources.collection()
        hits = await search(
            collection, query_vector,
            owner_uuid=query.owner_uuid, document_ids=query.document_ids,
        )
    except asyncio.CancelledError:
        raise
    except (SearchError, EmbeddingPreparationError):
        logger.warning("query_stream_failed stage=search code=SEARCH_ERROR")
        yield _sse("error", {"code": "SEARCH_ERROR"})
        return
    except Exception:
        logger.warning("query_stream_failed stage=search code=SEARCH_ERROR")
        yield _sse("error", {"code": "SEARCH_ERROR"})
        return

    # 관련도 필터: 거리가 기준보다 큰(덜 관련된) 조각을 버린다. 걸러진 결과를 sources와
    # LLM 근거 자료 양쪽에 똑같이 넘긴다. 전부 걸러지면 아래 0건 처리로 이어진다.
    hits = filter_by_distance(hits)

    # 3) 출처는 검색 메타데이터로 생성(0건이면 빈 배열). sources를 먼저 보낸다.
    yield _sse("sources", dedupe_sources(hits))

    # 4) 검색 0건이면 LLM을 만들지 않고 거절 문구만 보낸다. LLM 설정 오류가 0건
    #    거절 응답을 망치지 않도록, hits가 1건 이상일 때만 build_llm을 호출한다.
    if not hits:
        yield _sse("token", {"text": NO_CONTEXT_MESSAGE})
        yield _sse("done", {})
        return

    # 5) 답변 토큰 스트리밍. aclosing으로 감싸 어떤 이유로 중단되든(클라이언트 끊김
    #    → GeneratorExit/CancelledError) 안쪽 LLM 스트림이 즉시 닫히게 한다(비용 방어).
    answer_parts: list[str] = []
    try:
        llm = build_llm(settings)
        async with aclosing(astream_tokens(llm, query.question, hits)) as stream:
            async for text in stream:
                answer_parts.append(text)
                yield _sse("token", {"text": text})
    except asyncio.CancelledError:
        # 클라이언트 끊김: error를 보내지 않고 조용히 종료한다(비용 방어).
        raise
    except Exception:
        logger.warning("query_stream_failed stage=llm code=LLM_ERROR")
        yield _sse("error", {"code": "LLM_ERROR"})
        return

    # 6) 빈 답변 안전장치(#63): hits가 있는데 LLM이 실질 내용을 못 냈을 때(토큰 0개 또는
    #    공백만, 예: 추론 모델이 추론에 예산을 다 씀) done 대신 error를 보낸다. 공백 token이
    #    먼저 나갔더라도 Backend는 error면 저장하지 않는다. 검색 0건 거절 흐름(위 4)과 무관.
    if not "".join(answer_parts).strip():
        logger.warning("query_stream_failed stage=llm code=EMPTY_ANSWER")
        yield _sse("error", {"code": "EMPTY_ANSWER"})
        return

    # 7) 정상 완료. AI는 빈 객체만 보내고, chatId는 Backend가 붙인다.
    yield _sse("done", {})


@router.post("/internal/query/stream")
async def query_stream(request: Request):
    # 1) 토큰은 라우터 의존성이 이미 확인함(없으면 401). 2) JSON 파싱.
    try:
        raw = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "INVALID_INPUT"})

    # 3) 필드 검증. FastAPI 기본 422 대신 400 {"error":"INVALID_INPUT"}로 통일.
    try:
        query = QueryRequest.model_validate(raw)
    except (ValidationError, QueryInputError):
        return JSONResponse(status_code=400, content={"error": "INVALID_INPUT"})

    # 4) 여기까지 통과하면 SSE 응답을 시작한다.
    return StreamingResponse(
        _event_stream(request, query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
