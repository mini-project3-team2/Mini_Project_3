"""ASGI entry point: uvicorn src.api.main:app."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers.health import router as health_router
from src.core.config import Settings, load_settings


def create_app(settings_loader: Callable[[], Settings] = load_settings) -> FastAPI:
    """Validate settings at startup, once per application lifespan."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = settings_loader()
        try:
            yield
        finally:
            del application.state.settings

    application = FastAPI(title="AskNote AI", lifespan=lifespan)
    application.include_router(health_router)
    return application


app = create_app()
