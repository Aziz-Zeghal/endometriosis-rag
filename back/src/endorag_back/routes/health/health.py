"""GET /api/health: the active profile and its index."""

from endorag_ingestion.core.settings import Profile
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    profile: Profile
    collection: str
    points: int


@router.get("/health")
def health(request: Request) -> HealthResponse:
    settings, store = request.app.state.settings, request.app.state.store
    return HealthResponse(
        profile=settings.profile, collection=store.collection, points=store.count()
    )
