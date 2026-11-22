"""FastAPI application.

Run with `uvicorn endorag_back.routes.entrypoint:create_app --factory`: the settings are read
when the server starts, not when the module is imported.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import get_args

from endorag_ingestion.core.settings import Profile
from endorag_ingestion.factory import build_storage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient

from endorag_back.config.settings import Settings
from endorag_back.routes.chat import router as chat_router
from endorag_back.routes.health import router as health_router
from endorag_back.services.chat_service import ChatService

logger = logging.getLogger(__name__)

PROFILES: tuple[Profile, ...] = get_args(Profile)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Local Qdrant locks its directory, not a collection: one client for the app's
        # lifetime, shared by the store of each profile, closed at shutdown.
        client = QdrantClient(path=str(settings.qdrant_path))
        try:
            app.state.stores, app.state.chat_services = {}, {}
            for profile in PROFILES:
                profile_settings = settings.model_copy(update={"profile": profile})
                store = build_storage(profile_settings, client)
                app.state.stores[profile] = store
                app.state.chat_services[profile] = ChatService.from_settings(
                    profile_settings, store
                )
                logger.info("Profile %s, collection %s", profile, store.collection)
                # The store creates a missing collection: without this, a profile not yet
                # ingested would answer every question with a refusal and no sign of why.
                if store.count() == 0:
                    logger.warning(
                        "Profile %s: collection %s is empty, ingest it before asking questions",
                        profile,
                        store.collection,
                    )
            yield
        finally:
            client.close()

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
