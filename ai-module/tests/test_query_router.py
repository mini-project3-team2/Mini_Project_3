"""질의 스트리밍 라우터 테스트. TestClient + 모의 LLM·모의 임베딩·임시 Chroma.

실제 API 호출 없음. 출력 형식은 mock-data/internal/query-stream-*.txt,
query.400-invalid-input.json, query.401-unauthorized.json과 맞춘다.
"""

from contextlib import aclosing, asynccontextmanager
import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.chains.rag_chain import NO_CONTEXT_MESSAGE
from src.services.vectorstore import SearchError
from test_resources import test_settings

OWNER = "8f14e45f-ea4d-4bb0-9f17-a93e15de9032"
OTHER_OWNER = "11111111-1111-4111-8111-111111111111"
TOKEN = {"X-Internal-Token": "test-only-token"}
DIM = 1536


def unit_vector(axis: int) -> list[float]:
    vector = [0.0] * DIM
    vector[axis] = 1.0
    return vector


def parse_sse(text: str) -> list[tuple[str, str]]:
    """SSE 텍스트를 (event, data) 순서 리스트로 파싱한다."""
    events = []
    for block in text.split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = line[len("data: "):]
        if event is not None:
            events.append((event, data))
    return events


class FakeLLM:
    """astream으로 정해진 토큰 조각을 흘리는 모의 LLM. build_llm 대체용."""

    def __init__(self, pieces):
        self.pieces = pieces
        self.started = False

    def astream(self, messages):
        pieces = self.pieces

        async def gen():
            self.started = True
            for piece in pieces:
                yield SimpleNamespace(content=piece)

        return gen()


class QueryRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = test_settings(self.temp.name)

        # 모의 임베딩: 질문을 axis 0 방향 벡터로 임베딩(검색 결과를 예측 가능하게).
        self.embeddings = AsyncMock()
        self.embeddings.aembed_query.side_effect = lambda text: unit_vector(0)

        @asynccontextmanager
        async def fake_embeddings(settings):
            yield self.embeddings

        self.enterContext(patch("src.core.resources.open_embeddings", fake_embeddings))
        self.app = create_app(lambda: self.settings)
        self.client = self.enterContext(TestClient(self.app))

    # --- 유틸: 임시 Chroma에 합성 벡터 주입 -----------------------------------
    def seed(self, chunk_id, *, owner, document_id, name, page, axis, text="본문"):
        collection = self.client.portal.call(self.app.state.resources.collection)
        collection.add(
            ids=[chunk_id], documents=[text], embeddings=[unit_vector(axis)],
            metadatas=[{"owner_uuid": owner, "document_id": document_id,
                        "document_name": name, "page": page}],
        )

    def post(self, body, headers=TOKEN):
        return self.client.post("/internal/query/stream", headers=headers, json=body)

    def valid_body(self, **overrides):
        body = {"question": "질문입니다", "ownerUuid": OWNER, "documentIds": [12]}
        body.update(overrides)
        return body

    # --- 1. 인증 -------------------------------------------------------------
    def test_missing_or_wrong_token_is_401(self):
        for headers in ({}, {"X-Internal-Token": "wrong"}):
            response = self.client.post("/internal/query/stream", headers=headers,
                                        json=self.valid_body())
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_token_checked_before_body(self):
        # 토큰 없음 + 잘못된 본문 → 400이 아니라 401이어야 한다.
        response = self.client.post("/internal/query/stream", headers={}, content=b"not json")
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    # --- 2. 입력 검증 --------------------------------------------------------
    def test_malformed_json_is_400(self):
        response = self.client.post("/internal/query/stream", headers=TOKEN, content=b"{not json")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json(), {"error": "INVALID_INPUT"})

    def test_field_validation_failures_are_400(self):
        bad_bodies = [
            self.valid_body(question="   "),           # 공백만
            self.valid_body(question="x" * 1001),       # 1001자
            self.valid_body(ownerUuid="not-a-uuid"),    # uuid 형식
            self.valid_body(documentIds=[]),            # 빈 배열
            self.valid_body(documentIds=[0]),           # 범위 밖
            {"ownerUuid": OWNER, "documentIds": [12]},  # question 누락
        ]
        for body in bad_bodies:
            with self.subTest(body=body):
                response = self.post(body)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.json(), {"error": "INVALID_INPUT"})

    # --- 정상 흐름 -----------------------------------------------------------
    def test_success_order_sources_token_done(self):
        self.seed("c1", owner=OWNER, document_id=12, name="a.pdf", page=12, axis=0)
        with patch("src.api.routers.query.build_llm",
                   return_value=FakeLLM(["답변 ", "조각"])):
            response = self.post(self.valid_body())
        self.assertEqual(response.status_code, 200, response.text)
        events = parse_sse(response.text)
        names = [event for event, _ in events]
        self.assertEqual(names, ["sources", "token", "token", "done"])
        self.assertEqual(events[0][1], '[{"documentId":12,"documentName":"a.pdf","page":12}]')
        self.assertEqual(events[1][1], '{"text":"답변 "}')
        self.assertEqual(events[-1][1], "{}")  # done에 chatId 없음

    def test_zero_hits_sends_empty_sources_then_refusal(self):
        # 다른 소유자 청크만 있으면 이 사용자 검색 결과는 0건.
        self.seed("other", owner=OTHER_OWNER, document_id=12, name="x.pdf", page=1, axis=0)
        build = patch("src.api.routers.query.build_llm")
        with build as build_llm:
            response = self.post(self.valid_body())
            build_llm.assert_not_called()  # 0건이면 LLM 생성도 하지 않는다
        events = parse_sse(response.text)
        self.assertEqual([e for e, _ in events], ["sources", "token", "done"])
        self.assertEqual(events[0][1], "[]")
        import json
        self.assertEqual(json.loads(events[1][1])["text"], NO_CONTEXT_MESSAGE)

    # --- 오류 분기 -----------------------------------------------------------
    def test_embedding_error_sends_error_without_sources(self):
        self.embeddings.aembed_query.side_effect = RuntimeError("boom")
        response = self.post(self.valid_body())
        events = parse_sse(response.text)
        self.assertEqual([e for e, _ in events], ["error"])
        self.assertEqual(events[0][1], '{"code":"EMBEDDING_ERROR"}')

    def test_search_error_sends_error_without_sources(self):
        self.seed("c1", owner=OWNER, document_id=12, name="a.pdf", page=1, axis=0)
        with patch("src.api.routers.query.search", side_effect=SearchError("SEARCH_ERROR")):
            response = self.post(self.valid_body())
        events = parse_sse(response.text)
        self.assertEqual([e for e, _ in events], ["error"])
        self.assertEqual(events[0][1], '{"code":"SEARCH_ERROR"}')

    def test_llm_error_after_sources(self):
        self.seed("c1", owner=OWNER, document_id=12, name="a.pdf", page=5, axis=0)

        class BoomLLM:
            def astream(self, messages):
                async def gen():
                    yield SimpleNamespace(content="앞부분 ")
                    raise RuntimeError("llm down")
                return gen()

        with patch("src.api.routers.query.build_llm", return_value=BoomLLM()):
            response = self.post(self.valid_body())
        events = parse_sse(response.text)
        names = [e for e, _ in events]
        self.assertEqual(names, ["sources", "token", "error"])
        self.assertEqual(events[-1][1], '{"code":"LLM_ERROR"}')


class ClientDisconnectTests(unittest.IsolatedAsyncioTestCase):
    """클라이언트 끊김: 생성기를 소비하는 task를 첫 token 이후 cancel하면
    LLM astream이 취소·정리되고 error 이벤트가 나오지 않아야 한다(토큰 비용 방어).

    실제 서버는 클라이언트가 끊으면 응답 task를 cancel하므로, 테스트도 소비 task를
    돌리다 task.cancel()로 끊는다(aclose만으로는 안쪽 스트림에 취소가 안 간다)."""

    async def test_cancel_stops_llm_and_sends_no_error(self):
        from src.api.routers import query as query_module

        cancelled = {"value": False}

        class SlowLLM:
            def astream(self, messages):
                async def gen():
                    try:
                        yield SimpleNamespace(content="첫 토큰 ")
                        await asyncio.sleep(10)  # 두 번째 토큰 전에 끊길 것
                        yield SimpleNamespace(content="두 번째")
                    finally:
                        # aclosing 정리 시 GeneratorExit로 닫힐 수 있으므로 finally에서 표시.
                        cancelled["value"] = True
                return gen()

        hit = SimpleNamespace(document_id=1, document_name="a.pdf", page=1, text="t")

        async def fake_search(collection, vector, *, owner_uuid, document_ids, k=4):
            return [hit]

        embeddings = AsyncMock()
        embeddings.aembed_query.side_effect = lambda text: [0.0] * DIM
        resources = SimpleNamespace(
            embeddings=AsyncMock(return_value=embeddings),
            collection=AsyncMock(return_value=object()),
        )
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            resources=resources, settings=object())))
        query = SimpleNamespace(question="q", owner_uuid=OWNER, document_ids=[1])

        collected = []
        # 첫 token을 받으면 신호를 주는 이벤트. 그 뒤 소비 task를 cancel한다.
        got_token = asyncio.Event()

        async def consume():
            async with aclosing(query_module._event_stream(request, query)) as stream:
                async for chunk in stream:
                    collected.append(chunk)
                    if chunk.startswith(b"event: token"):
                        got_token.set()
                        # 여기서 멈추지 않고 다음 __anext__로 넘어가 SlowLLM의 sleep에서
                        # 대기하게 둔다. 그래야 cancel이 LLM 대기 지점에 떨어진다.

        with patch.object(query_module, "search", fake_search), \
             patch.object(query_module, "build_llm", return_value=SlowLLM()), \
             patch.object(query_module, "dedupe_sources", return_value=[]):
            task = asyncio.create_task(consume())
            await asyncio.wait_for(got_token.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        # sources와 첫 token까지는 나갔다.
        self.assertTrue(collected[0].startswith(b"event: sources"))
        self.assertTrue(any(c.startswith(b"event: token") for c in collected))
        # LLM 스트림이 취소·정리되었다.
        self.assertTrue(cancelled["value"])
        # 두 번째 토큰은 생성되지 않았다(끊김으로 LLM이 멈춤).
        self.assertTrue(all("두 번째" not in c.decode("utf-8") for c in collected))
        # error 이벤트는 생성되지 않았다(조용히 종료).
        self.assertFalse(any(c.startswith(b"event: error") for c in collected))


if __name__ == "__main__":
    unittest.main()
