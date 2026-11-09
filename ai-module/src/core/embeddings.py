"""Shared, explicitly owned OpenAI embedding clients; construction makes no requests."""

from contextlib import AsyncExitStack, asynccontextmanager

from langchain_openai import OpenAIEmbeddings
from openai import AsyncOpenAI, OpenAI

from src.core.config import Settings


@asynccontextmanager
async def open_embeddings(settings: Settings):
    api_key = settings.require_embedding_api_key()
    # No SDK retries: the ingestion service will own the total time budget.
    options = dict(api_key=api_key, base_url="https://api.openai.com/v1",
                   timeout=30.0, max_retries=0)
    async with AsyncExitStack() as stack:
        sync_client = stack.enter_context(OpenAI(**options))
        async_client = await stack.enter_async_context(AsyncOpenAI(**options))
        yield OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=api_key,
            client=sync_client.embeddings,
            async_client=async_client.embeddings,
            # Use default model dimensions (1536); do not shorten vectors.
            dimensions=None,
            chunk_size=64,
            max_retries=0,
            request_timeout=30.0,
            # Input sizing belongs to ingestion/query; avoid hidden token splitting
            # and tokenizer downloads here.
            check_embedding_ctx_length=False,
        )
