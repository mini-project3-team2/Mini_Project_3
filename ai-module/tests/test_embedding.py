import asyncio
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.documents import Document
from openai import OpenAIError

from src.services.embedding import embed_chunks, EmbeddingPreparationError
from src.services.pdf import prepare_pdf
from test_pdf import synthetic_pdf


def chunk(text="sample", page=1):
    return Document(page_content=text, metadata={
        "owner_uuid": "8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
        "document_id": 12, "document_name": "sample.pdf", "page": page,
    })


class EmbeddingTests(unittest.IsolatedAsyncioTestCase):
    def client(self):
        client = AsyncMock()
        client.aembed_documents.side_effect = lambda texts: [[1.0] + [0.0] * 1535 for _ in texts]
        return client

    async def test_pdf_to_validated_vectors_without_storage(self):
        with TemporaryDirectory() as directory:
            documents = await asyncio.to_thread(
                prepare_pdf, io.BytesIO(synthetic_pdf(["first", "", "third"])),
                "sample.pdf", temp_directory=Path(directory),
                owner_uuid="8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
                document_id=12, document_name="sample.pdf",
            )
            result = await embed_chunks(documents, self.client())
            self.assertEqual([item.metadata["page"] for item in result], [1, 3])
            self.assertEqual([item.text for item in result], ["first", "third"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_batches_keep_order_and_snapshot_metadata(self):
        client = self.client()
        inputs = [chunk(str(i), i + 1) for i in range(65)]
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            result = await embed_chunks(inputs, client)
        self.assertEqual([len(call.args[0]) for call in client.aembed_documents.call_args_list], [64, 1])
        self.assertEqual([r.text for r in result], [str(i) for i in range(65)])
        self.assertEqual([r.metadata["page"] for r in result], list(range(1, 66)))
        self.assertEqual(len(result[0].vector), 1536)
        inputs[0].metadata["page"] = 999
        self.assertEqual(result[0].metadata["page"], 1)
        self.assertNotIn("sample.pdf", repr(result))

    async def test_invalid_later_input_prevents_all_calls(self):
        for text in ("", "  ", "a" * 801, "\ud800"):
            client = self.client()
            with self.subTest(text_length=len(text)):
                with self.assertRaises(EmbeddingPreparationError) as caught:
                    await embed_chunks([chunk()] * 64 + [chunk(text)], client)
                self.assertEqual(caught.exception.code, "INVALID_INPUT")
                client.aembed_documents.assert_not_called()

    async def test_empty_input_and_invalid_metadata(self):
        for inputs in ([], [Document(page_content="x")], [chunk(page=True)]):
            client = self.client()
            with self.assertRaises(EmbeddingPreparationError):
                await embed_chunks(inputs, client)
            client.aembed_documents.assert_not_called()

    async def test_unicode_at_character_limit(self):
        client = self.client()
        result = await embed_chunks([chunk("😀" * 800)] * 64, client)
        self.assertEqual(len(result), 64)
        client.aembed_documents.assert_awaited_once()

    async def test_malformed_vectors(self):
        bad = [None, [], [[1.0]], [[0.0] * 1536]]
        for value in (float("nan"), float("inf"), True, "1", 10 ** 400):
            bad.append([[value] + [0.0] * 1535])
        for raw in bad:
            with self.subTest(kind=str(type(raw))):
                client = AsyncMock()
                client.aembed_documents.return_value = raw
                with self.assertRaises(EmbeddingPreparationError) as caught:
                    await embed_chunks([chunk()], client)
                self.assertEqual(caught.exception.code, "EMBEDDING_ERROR")
                client.aembed_documents.assert_awaited_once()

    async def test_later_batch_failure_no_retry_or_partial_return(self):
        client = AsyncMock()
        client.aembed_documents.side_effect = [
            [[1.0] * 1536 for _ in range(64)], OpenAIError("private provider detail")
        ]
        with self.assertRaises(EmbeddingPreparationError) as caught:
            await embed_chunks([chunk()] * 65, client)
        self.assertEqual(str(caught.exception), "EMBEDDING_ERROR")
        self.assertEqual(client.aembed_documents.await_count, 2)

    async def test_expired_budget_prevents_call(self):
        client = self.client()
        with self.assertRaises(EmbeddingPreparationError) as caught:
            await embed_chunks([chunk()], client, budget_seconds=0)
        self.assertEqual(caught.exception.code, "INGESTION_TIMEOUT")
        client.aembed_documents.assert_not_called()

    async def test_timeouts_cancel_request_and_classify_budget(self):
        for budget, request_limit, expected in (
            (0.01, 30, "INGESTION_TIMEOUT"), (1, 0.01, "EMBEDDING_ERROR")
        ):
            cancelled = asyncio.Event()
            async def blocked(texts):
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
            client = AsyncMock()
            client.aembed_documents.side_effect = blocked
            with patch("src.services.embedding.REQUEST_TIMEOUT_SECONDS", request_limit):
                with self.assertRaises(EmbeddingPreparationError) as caught:
                    await embed_chunks([chunk()], client, budget_seconds=budget)
            self.assertEqual(caught.exception.code, expected)
            self.assertTrue(cancelled.is_set())

    async def test_caller_cancellation_propagates(self):
        client = AsyncMock()
        client.aembed_documents.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await embed_chunks([chunk()], client)


if __name__ == "__main__":
    unittest.main()
