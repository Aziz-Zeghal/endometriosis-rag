"""FastAPI application.

Run with `uvicorn endorag_back.routes.entrypoint:create_app --factory`: the settings are read
when the server starts, not when the module is imported.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from endorag_ingestion.factory import build_storage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from endorag_back.config.settings import Settings
from endorag_back.routes.chat import router as chat_router
from endorag_back.routes.health import router as health_router
from endorag_back.services.chat_service import ChatService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Local Qdrant locks its directory: one store for the app's lifetime, closed at shutdown.
        app.state.store = build_storage(settings)
        app.state.chat_service = ChatService.from_settings(settings, app.state.store)
        logger.info("Profile %s, collection %s", settings.profile, settings.collection_name())
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(title="endorag", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    return app
