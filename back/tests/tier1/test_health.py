from endorag_back.config.settings import Settings
from endorag_back.routes import entrypoint
from fastapi.testclient import TestClient


class FakeStore:
    def __init__(self, collection: str) -> None:
        self.collection = collection
        self.closed = False

    def count(self) -> int:
        return 741

    def close(self) -> None:
        self.closed = True


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        profile="gp",
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
        cors_origins=["https://host.test"],
    )


def test_health_reports_profile_collection_and_points(monkeypatch):
    stores: list[FakeStore] = []

    def fake_build_storage(settings):
        stores.append(FakeStore(settings.collection_name()))
        return stores[-1]

    monkeypatch.setattr(entrypoint, "build_storage", fake_build_storage)
    with TestClient(entrypoint.create_app(make_settings())) as client:
        response = client.get("/api/health")
        assert len(stores) == 1  # created once at startup, not per request
        assert not stores[0].closed
        client.get("/api/health")
        assert len(stores) == 1
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "profile": "gp",
        "collection": "gp__nemotron-3-embed-1b",
        "points": 741,
    }
    assert stores[0].closed  # released at shutdown (local Qdrant locks its directory)


def test_cors_allows_configured_origins_only(monkeypatch):
    monkeypatch.setattr(entrypoint, "build_storage", lambda s: FakeStore(s.collection_name()))
    with TestClient(entrypoint.create_app(make_settings())) as client:
        allowed = client.get("/api/health", headers={"Origin": "https://host.test"})
        other = client.get("/api/health", headers={"Origin": "https://evil.test"})
    assert allowed.headers["access-control-allow-origin"] == "https://host.test"
    assert "access-control-allow-origin" not in other.headers
