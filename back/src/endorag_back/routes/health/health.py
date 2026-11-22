"""GET /api/health: the index of each profile the app serves."""

from endorag_ingestion.core.settings import Profile
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class ProfileHealth(BaseModel):
    collection: str
    points: int


class HealthResponse(BaseModel):
    status: str = "ok"
    default_profile: Profile  # used when a chat request names no profile
    profiles: dict[Profile, ProfileHealth]


@router.get("/health")
def health(request: Request) -> HealthResponse:
    stores = request.app.state.stores
    return HealthResponse(
        default_profile=request.app.state.settings.profile,
        profiles={
            profile: ProfileHealth(collection=store.collection, points=store.count())
            for profile, store in stores.items()
        },
    )
