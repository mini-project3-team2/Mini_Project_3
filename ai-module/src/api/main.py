"""ASGI entry point: uvicorn src.api.main:app."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers.health import router as health_router
from src.api.routers.documents import router as documents_router
from src.core.config import Settings, load_settings
from src.core.resources import AppResources


def create_app(settings_loader: Callable[[], Settings] = load_settings) -> FastAPI:
    """Validate settings at startup, once per application lifespan."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = settings_loader()
        application.state.resources = AppResources(application.state.settings)
        try:
            yield
        finally:
            try:
                await application.state.resources.aclose()
            finally:
                del application.state.resources
                del application.state.settings

    application = FastAPI(title="AskNote AI", lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(documents_router)
    return application


app = create_app()
