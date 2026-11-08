"""질의 요청 스키마(QueryRequest) 단위 테스트. 외부 호출 없음."""

import unittest

from pydantic import ValidationError

from src.schemas.query import QueryRequest

OWNER = "8f14e45f-ea4d-4bb0-9f17-a93e15de9032"


def body(**overrides):
    data = {"question": "질문입니다", "ownerUuid": OWNER, "documentIds": [12]}
    data.update(overrides)
    return data


class QuerySchemaTests(unittest.TestCase):
    def test_valid_request_trims_and_normalizes(self):
        req = QueryRequest.model_validate(
            body(question="  JWT 회전은 왜? ", ownerUuid=OWNER.upper(), documentIds=[12, 15])
        )
        # question은 strip되고, ownerUuid는 소문자로 정규화된다.
        self.assertEqual(req.question, "JWT 회전은 왜?")
        self.assertEqual(req.owner_uuid, OWNER)
        self.assertEqual(req.document_ids, [12, 15])

    def test_question_boundaries(self):
        # 1자·1000자(strip 후)는 통과, 0자(공백만)·1001자는 거부.
        self.assertEqual(QueryRequest.model_validate(body(question="x")).question, "x")
        ok = QueryRequest.model_validate(body(question="x" * 1000))
        self.assertEqual(len(ok.question), 1000)
        for bad in ("", "   ", "x" * 1001):
            with self.subTest(q=bad[:5] + f"...len={len(bad)}"):
                with self.assertRaises(ValidationError):
                    QueryRequest.model_validate(body(question=bad))

    def test_question_strip_counts_trimmed_length(self):
        # 앞뒤 공백 포함 1002자지만 strip 후 1000자면 통과해야 한다.
        padded = " " + "x" * 1000 + " "
        self.assertEqual(len(QueryRequest.model_validate(body(question=padded)).question), 1000)
        # strip 후 1001자는 거부.
        with self.assertRaises(ValidationError):
            QueryRequest.model_validate(body(question=" " + "x" * 1001 + " "))

    def test_owner_uuid_format(self):
        for bad in ("not-a-uuid", OWNER.replace("-", ""), " " + OWNER, OWNER + "x"):
            with self.subTest(uuid=bad):
                with self.assertRaises(ValidationError):
                    QueryRequest.model_validate(body(ownerUuid=bad))

    def test_document_ids_rules(self):
        # 정상: 1개 이상, 범위 안.
        self.assertEqual(QueryRequest.model_validate(body(documentIds=[1])).document_ids, [1])
        self.assertEqual(
            QueryRequest.model_validate(body(documentIds=[9223372036854775807])).document_ids,
            [9223372036854775807],
        )
        for bad in ([], [0], [-1], [9223372036854775808], [12, 0], ["12"], [True]):
            with self.subTest(ids=bad):
                with self.assertRaises(ValidationError):
                    QueryRequest.model_validate(body(documentIds=bad))

    def test_extra_field_is_rejected(self):
        with self.assertRaises(ValidationError):
            QueryRequest.model_validate(body(unexpected="x"))

    def test_missing_fields_are_rejected(self):
        for missing in ("question", "ownerUuid", "documentIds"):
            with self.subTest(missing=missing):
                data = {k: v for k, v in body().items() if k != missing}
                with self.assertRaises(ValidationError):
                    QueryRequest.model_validate(data)


if __name__ == "__main__":
    unittest.main()
