import asyncio
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from openai import AsyncOpenAI, OpenAI

from src.core.config import AI_MODULE_DIR, ConfigurationError, load_settings
from src.core.embeddings import open_embeddings
from src.core.resources import AppResources
from src.services.vectorstore import open_collection


def test_settings(directory="", key="test-only-key"):
    return load_settings(env_file=None, environ={
        "AI_INTERNAL_TOKEN": "test-only-token",
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "OPENAI_API_KEY": key,
        "CHROMA_PERSIST_DIRECTORY": directory,
    })


class ResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_construction_no_network_and_both_clients_close(self):
        clients = []

        def sync_factory(**kwargs):
            client = OpenAI(**kwargs)
            clients.append(client)
            return client

        def async_factory(**kwargs):
            client = AsyncOpenAI(**kwargs)
            clients.append(client)
            return client

        with patch("src.core.embeddings.OpenAI", side_effect=sync_factory), \
             patch("src.core.embeddings.AsyncOpenAI", side_effect=async_factory), \
             patch("socket.socket.connect", side_effect=AssertionError("Unexpected network")):
            async with open_embeddings(test_settings()) as embeddings:
                self.assertEqual(embeddings.model, "text-embedding-3-small")
                self.assertIsNone(embeddings.dimensions)
                self.assertFalse(embeddings.check_embedding_ctx_length)
                for client in clients:
                    self.assertEqual(str(client.base_url), "https://api.openai.com/v1/")
                    self.assertEqual(client.max_retries, 0)
                    self.assertFalse(client.is_closed())
            self.assertTrue(all(client.is_closed() for client in clients))

    async def test_missing_key_does_not_create_client(self):
        with patch("src.core.embeddings.OpenAI") as factory:
            with self.assertRaises(ConfigurationError):
                async with open_embeddings(test_settings(key="")):
                    self.fail("Missing key must be rejected")
            factory.assert_not_called()

    async def test_partial_sdk_initialization_failure_closes_sync_client(self):
        client = OpenAI(api_key="test-only-key")
        with patch("src.core.embeddings.OpenAI", return_value=client), \
             patch("src.core.embeddings.AsyncOpenAI", side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError):
                async with open_embeddings(test_settings()):
                    pass
        self.assertTrue(client.is_closed())

    async def test_concurrent_first_use_reuses_instances_and_closes_once(self):
        opened, closed = [], []

        @asynccontextmanager
        async def factory(settings):
            resource = object()
            opened.append(resource)
            await asyncio.sleep(0)
            try:
                yield resource
            finally:
                closed.append(resource)

        resources = AppResources(test_settings())
        self.assertEqual(opened, [])
        with patch("src.core.resources.open_embeddings", factory), \
             patch("src.core.resources.open_collection", factory):
            embeddings = await asyncio.gather(*(resources.embeddings() for _ in range(10)))
            collections = await asyncio.gather(*(resources.collection() for _ in range(10)))
            self.assertTrue(all(item is embeddings[0] for item in embeddings))
            self.assertTrue(all(item is collections[0] for item in collections))
            self.assertEqual(len(opened), 2)
            await resources.aclose()
            await resources.aclose()
            self.assertEqual(closed, list(reversed(opened)))
            with self.assertRaises(RuntimeError):
                await resources.embeddings()

    async def test_failed_creation_can_be_retried(self):
        resources = AppResources(test_settings(key=""))
        for _ in range(2):
            with self.assertRaises(ConfigurationError):
                await resources.embeddings()
        await resources.aclose()

    async def test_real_chroma_persistence_and_no_default_embedding(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = test_settings(directory)
            with patch("socket.socket.connect", side_effect=AssertionError("Unexpected network")):
                async with open_collection(settings) as collection:
                    self.assertEqual(collection.name, settings.collection_name)
                    with self.assertRaises(ValueError):
                        collection.add(ids=["no-vector"], documents=["synthetic test"])
                    self.assertEqual(collection.count(), 0)
                    collection.add(ids=["explicit-vector"], embeddings=[[0.1] * 1536],
                                   documents=["synthetic test"])
                async with open_collection(settings) as reopened:
                    self.assertEqual(reopened.count(), 1)
                    self.assertEqual(reopened.get()["ids"], ["explicit-vector"])
                    with self.assertRaises(ValueError):
                        reopened.query(query_texts=["synthetic question"], n_results=1)
                    self.assertEqual(reopened.query(query_embeddings=[[0.1] * 1536],
                                                    n_results=1)["ids"], [["explicit-vector"]])

    async def test_collection_failure_closes_client(self):
        with patch("src.services.vectorstore.chromadb.PersistentClient") as factory:
            factory.return_value.get_or_create_collection.side_effect = RuntimeError("injected")
            with self.assertRaises(RuntimeError):
                async with open_collection(test_settings()):
                    pass
            factory.return_value.close.assert_called_once_with()

    def test_paths_have_stable_base(self):
        self.assertEqual(test_settings().chroma_persist_directory, AI_MODULE_DIR / "chroma_db")
        self.assertEqual(test_settings("isolated-test").chroma_persist_directory,
                         AI_MODULE_DIR / "isolated-test")
        self.assertEqual(test_settings(str(Path.cwd())).chroma_persist_directory, Path.cwd())
