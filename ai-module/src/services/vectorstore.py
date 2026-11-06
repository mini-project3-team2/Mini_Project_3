"""Persistent collection with no implicit embedding provider."""

import asyncio
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
