"""소유자 필터 검색 단위 테스트. 임시 Chroma + 합성 벡터만 사용(실제 API 호출 없음).

이 프로젝트의 핵심 보안(사용자별 문서 격리)을 검증한다:
1) 다른 owner_uuid의 청크는 검색되지 않는다.
2) documentIds에 없는 문서(READY가 아닌 문서)의 청크는 검색되지 않는다.
3) 결과는 검색 순서대로, 중복 제거 없이 반환된다.
"""

import tempfile
import unittest

from src.services.vectorstore import DEFAULT_K, SearchHit, open_collection, search
from test_resources import test_settings

OWNER = "8f14e45f-ea4d-4bb0-9f17-a93e15de9032"
OTHER_OWNER = "11111111-1111-4111-8111-111111111111"
DIM = 1536


def unit_vector(index: int) -> list[float]:
    """해당 축만 1인 1536차원 단위 벡터. 질의 벡터로 '가까운 청크'를 제어한다."""
    vector = [0.0] * DIM
    vector[index] = 1.0
    return vector


class OwnerFilterSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = test_settings(self.temp.name)
        self.context = open_collection(self.settings)
        self.collection = await self.context.__aenter__()
        self.addAsyncCleanup(self.context.__aexit__, None, None, None)

    def add_chunk(self, chunk_id, *, owner, document_id, document_name, page, axis):
        """합성 벡터 한 건을 Chroma에 직접 넣는다(임베딩 모델 호출 없음)."""
        self.collection.add(
            ids=[chunk_id],
            documents=[f"text-{chunk_id}"],
            embeddings=[unit_vector(axis)],
            metadatas=[{
                "owner_uuid": owner,
                "document_id": document_id,
                "document_name": document_name,
                "page": page,
            }],
        )

    async def test_other_owner_chunks_are_never_returned(self):
        # 같은 축(=질의와 동일 방향) 벡터지만 소유자가 다르면 검색되면 안 된다.
        self.add_chunk("mine", owner=OWNER, document_id=12, document_name="mine.pdf", page=1, axis=0)
        self.add_chunk("theirs", owner=OTHER_OWNER, document_id=12, document_name="theirs.pdf", page=1, axis=0)

        hits = await search(
            self.collection, unit_vector(0),
            owner_uuid=OWNER, document_ids=[12], k=DEFAULT_K,
        )
        names = {hit.document_name for hit in hits}
        self.assertEqual(names, {"mine.pdf"})
        self.assertTrue(all(hit.document_name != "theirs.pdf" for hit in hits))

    async def test_documents_not_in_id_list_are_never_returned(self):
        # 같은 소유자라도 documentIds(READY 목록)에 없는 문서는 제외된다.
        self.add_chunk("ready", owner=OWNER, document_id=12, document_name="ready.pdf", page=1, axis=0)
        self.add_chunk("not-ready", owner=OWNER, document_id=99, document_name="not-ready.pdf", page=1, axis=0)

        hits = await search(
            self.collection, unit_vector(0),
            owner_uuid=OWNER, document_ids=[12], k=DEFAULT_K,
        )
        ids = {hit.document_id for hit in hits}
        self.assertEqual(ids, {12})
        self.assertNotIn(99, ids)

    async def test_results_keep_search_order_without_dedupe(self):
        # 같은 페이지의 청크 2개 + 다른 페이지 1개. 질의 벡터와의 거리로 순서를 만든다.
        # axis 0에 가장 가깝고, axis 1, axis 2 순으로 멀어지게 질의 벡터를 구성한다.
        self.add_chunk("p12-a", owner=OWNER, document_id=1, document_name="a.pdf", page=12, axis=0)
        self.add_chunk("p12-b", owner=OWNER, document_id=1, document_name="a.pdf", page=12, axis=1)
        self.add_chunk("p14", owner=OWNER, document_id=1, document_name="a.pdf", page=14, axis=2)

        # axis 0 > axis 1 > axis 2 순으로 유사도가 높도록 가중한 질의 벡터.
        query = [0.0] * DIM
        query[0], query[1], query[2] = 0.9, 0.6, 0.3

        hits = await search(
            self.collection, query,
            owner_uuid=OWNER, document_ids=[1], k=DEFAULT_K,
        )
        # 중복 제거 없이 3건 모두, 유사도 순서(page 12, page 12, page 14)로 반환.
        self.assertEqual(len(hits), 3)
        self.assertEqual([hit.page for hit in hits], [12, 12, 14])
        self.assertTrue(all(isinstance(hit, SearchHit) for hit in hits))

    async def test_empty_document_ids_skips_search(self):
        self.add_chunk("mine", owner=OWNER, document_id=12, document_name="mine.pdf", page=1, axis=0)
        hits = await search(
            self.collection, unit_vector(0),
            owner_uuid=OWNER, document_ids=[], k=DEFAULT_K,
        )
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
