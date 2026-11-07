"""One lazily initialized set of clients per application lifespan."""

import asyncio
from contextlib import AsyncExitStack

from fastapi import Request

from src.core.config import Settings
from src.core.embeddings import open_embeddings
from src.services.vectorstore import open_collection
from src.services.ingest import IngestionCoordinator


class AppResources:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._embeddings = None
        self._collection = None
        self._closed = False
        self.ingestion = IngestionCoordinator()

    async def _get(self, attribute, factory):
        async with self._lock:
            if self._closed:
                raise RuntimeError("Application resources are closed")
            value = getattr(self, attribute)
            if value is None:
                value = await self._stack.enter_async_context(factory(self._settings))
                setattr(self, attribute, value)
            return value

    async def embeddings(self):
        return await self._get("_embeddings", open_embeddings)

    async def collection(self):
        return await self._get("_collection", open_collection)

    async def aclose(self):
        async with self._lock:
            if not self._closed:
                self._closed = True
                try:
                    await self._stack.aclose()
                finally:
                    self._embeddings = self._collection = None


async def get_embeddings(request: Request):
    return await request.app.state.resources.embeddings()


async def get_collection(request: Request):
    return await request.app.state.resources.collection()
