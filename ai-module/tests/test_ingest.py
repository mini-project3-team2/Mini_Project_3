import asyncio
import io
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from src.services.ingest import IngestionCoordinator, IngestionError
from src.services.vectorstore import open_collection
from src.services.pdf import prepare_pdf
from test_resources import test_settings
from test_embedding import chunk
from test_pdf import synthetic_pdf


class CollectionProxy:
    """Inject failures around real local Chroma, not a replacement database."""
    def __init__(self, collection):
        self.collection = collection

    def __getattr__(self, name):
        return getattr(self.collection, name)


class IngestionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = test_settings(self.temp.name)
        self.context = open_collection(self.settings)
        self.collection = await self.context.__aenter__()
        self.addAsyncCleanup(self.context.__aexit__, None, None, None)
        self.service = IngestionCoordinator()
        self.client = AsyncMock()
        self.client.aembed_documents.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]

    async def ingest(self, documents=None, **kwargs):
        return await self.service.ingest(documents or [chunk()], self.client,
                                         kwargs.pop("collection", self.collection), **kwargs)

    async def test_pdf_to_persistent_chroma_and_duplicate_without_embedding(self):
        with tempfile.TemporaryDirectory() as pdf_temp:
            documents = await asyncio.to_thread(
                prepare_pdf, io.BytesIO(synthetic_pdf(["first", "", "third"])), "sample.pdf",
                owner_uuid=chunk().metadata["owner_uuid"], document_id=12,
                document_name="sample.pdf", temp_directory=Path(pdf_temp),
            )
        result = await self.ingest(documents)
        self.assertEqual((result.document_id, result.chunk_count), (12, 2))
        rows = self.collection.get(include=["documents", "metadatas", "embeddings"])
        self.assertEqual(set(rows["documents"]), {"first", "third"})
        self.assertEqual({m["page"] for m in rows["metadatas"]}, {1, 3})
        self.assertTrue(all(len(v) == 1536 for v in rows["embeddings"]))
        self.assertEqual(set(rows["ids"]), {f'{chunk().metadata["owner_uuid"]}:12:{i}' for i in range(2)})
        async with open_collection(self.settings) as reopened:
            self.assertEqual(reopened.get()["ids"], rows["ids"])
        self.client.aembed_documents.reset_mock()
        with self.assertRaises(IngestionError) as caught:
            await self.ingest(documents)
        self.assertEqual(caught.exception.code, "DOCUMENT_ALREADY_EXISTS")
        self.client.aembed_documents.assert_not_called()
        self.assertEqual(self.collection.count(), 2)

    async def seed_other_documents(self):
        other_owner = chunk()
        other_owner.metadata["owner_uuid"] = "11111111-1111-4111-8111-111111111111"
        other_doc = chunk()
        other_doc.metadata["document_id"] = 99
        await self.ingest([other_owner])
        await self.ingest([other_doc])
        return set(self.collection.get()["ids"])

    async def test_partial_second_batch_rolls_back_only_this_request(self):
        preserved = await self.seed_other_documents()
        class PartialFailure(CollectionProxy):
            calls = 0
            def add(self, **kwargs):
                self.calls += 1
                if self.calls == 2:
                    self.collection.add(**{k: v[:1] for k, v in kwargs.items()})
                    raise RuntimeError("private failure detail")
                self.collection.add(**kwargs)
        with self.assertRaises(IngestionError) as caught:
            await self.ingest([chunk(str(i)) for i in range(65)], collection=PartialFailure(self.collection))
        self.assertEqual(str(caught.exception), "STORAGE_ERROR")
        self.assertEqual(set(self.collection.get()["ids"]), preserved)
        # Guard was released and failed document can now be retried.
        self.assertEqual((await self.ingest()).chunk_count, 1)

    async def test_count_mismatch_rolls_back(self):
        class MissingWrite(CollectionProxy):
            def add(self, **kwargs):
                self.collection.add(**{k: v[:1] for k, v in kwargs.items()})
        with self.assertRaises(IngestionError):
            await self.ingest([chunk("a"), chunk("b")], collection=MissingWrite(self.collection))
        self.assertEqual(self.collection.count(), 0)

    async def test_cleanup_failure_is_reported_and_residue_blocks_retry(self):
        class BrokenCleanup(CollectionProxy):
            def add(self, **kwargs):
                self.collection.add(**kwargs)
                raise RuntimeError("write error")
            def delete(self, **kwargs):
                raise RuntimeError("delete error")
        with self.assertLogs("src.services.ingest", level="ERROR") as logs:
            with self.assertRaises(IngestionError) as caught:
                await self.ingest(collection=BrokenCleanup(self.collection))
        self.assertEqual(caught.exception.code, "STORAGE_ERROR")
        self.assertIn("ingestion_cleanup_failed", logs.output[0])
        self.assertEqual(self.collection.count(), 1)
        with self.assertRaises(IngestionError) as duplicate:
            await self.ingest()
        self.assertEqual(duplicate.exception.code, "DOCUMENT_ALREADY_EXISTS")

    async def test_same_document_conflicts_other_document_can_continue(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def delayed(texts):
            started.set()
            await release.wait()
            return [[0.1] * 1536 for _ in texts]
        self.client.aembed_documents.side_effect = delayed
        first = asyncio.create_task(self.ingest())
        try:
            await asyncio.wait_for(started.wait(), 2)
            with self.assertRaises(IngestionError) as caught:
                await self.ingest()
            self.assertEqual(caught.exception.code, "INGESTION_IN_PROGRESS")
            other = chunk()
            other.metadata["document_id"] = 13
            fast_client = AsyncMock()
            fast_client.aembed_documents.return_value = [[0.1] * 1536]
            result = await self.service.ingest([other], fast_client, self.collection)
            self.assertEqual(result.document_id, 13)
        finally:
            release.set()
            await first
        self.assertEqual(self.collection.count(), 2)

    async def test_cancel_during_write_waits_then_cleans_no_late_records(self):
        started, release = threading.Event(), threading.Event()
        class SlowWrite(CollectionProxy):
            def add(self, **kwargs):
                started.set()
                if not release.wait(3):
                    raise RuntimeError("test release timeout")
                self.collection.add(**kwargs)
        task = asyncio.create_task(self.ingest(collection=SlowWrite(self.collection)))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()  # repeated cancellation must still hold the guard
            with self.assertRaises(IngestionError) as caught:
                await self.ingest()
            self.assertEqual(caught.exception.code, "INGESTION_IN_PROGRESS")
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.collection.count(), 0)
        self.assertEqual((await self.ingest()).chunk_count, 1)

    async def test_timeout_after_write_rolls_back(self):
        class SlowWrite(CollectionProxy):
            def add(self, **kwargs):
                self.collection.add(**kwargs)
                time.sleep(0.05)
        with self.assertRaises(IngestionError) as caught:
            await self.ingest(collection=SlowWrite(self.collection), budget_seconds=0.04)
        self.assertEqual(caught.exception.code, "INGESTION_TIMEOUT")
        self.assertEqual(self.collection.count(), 0)

    async def test_mixed_document_input_is_rejected_before_embedding(self):
        other = chunk()
        other.metadata["document_id"] = 13
        with self.assertRaises(IngestionError) as caught:
            await self.ingest([chunk(), other])
        self.assertEqual(caught.exception.code, "INVALID_INPUT")
        self.client.aembed_documents.assert_not_called()
        self.assertEqual(self.collection.count(), 0)

    async def test_close_and_reopen_preserves_ingested_records(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = test_settings(directory)
            async with open_collection(settings) as collection:
                await self.service.ingest([chunk("persistent")], self.client, collection)
            async with open_collection(settings) as reopened:
                rows = reopened.get(include=["documents", "metadatas"])
                self.assertEqual(rows["documents"], ["persistent"])
                self.assertEqual(rows["metadatas"][0]["document_id"], 12)


if __name__ == "__main__":
    unittest.main()
