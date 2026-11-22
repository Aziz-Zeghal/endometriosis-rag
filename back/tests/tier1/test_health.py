from typing import ClassVar

from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.routes import entrypoint
from fastapi.testclient import TestClient

POINTS = {"patient": 741, "gp": 364}


class FakeClient:
    """Stands in for the local QdrantClient the app opens once for both profiles."""

    instances: ClassVar[list["FakeClient"]] = []

    def __init__(self, path: str) -> None:
        self.path = path
        self.closed = False
        FakeClient.instances.append(self)

    def close(self) -> None:
        self.closed = True


class FakeStore:
    def __init__(self, collection: str, client: FakeClient) -> None:
        self.collection = collection
        self.client = client

    def count(self) -> int:
        return POINTS[self.collection.split("__")[0]]


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


def patch_storage(monkeypatch) -> list[FakeStore]:
    stores: list[FakeStore] = []

    def fake_build_storage(settings, client):
        stores.append(FakeStore(settings.collection_name(), client))
        return stores[-1]

    FakeClient.instances = []
    monkeypatch.setattr(entrypoint, "QdrantClient", FakeClient)
    monkeypatch.setattr(entrypoint, "build_storage", fake_build_storage)
    return stores


def test_health_reports_both_profiles(monkeypatch):
    stores = patch_storage(monkeypatch)
    with TestClient(entrypoint.create_app(make_settings())) as client:
        response = client.get("/api/health")
        client.get("/api/health")
        assert len(stores) == 2  # one per profile, created once at startup, not per request
        assert len(FakeClient.instances) == 1  # sharing one client: the lock is per directory
        assert all(s.client is FakeClient.instances[0] for s in stores)
        assert not FakeClient.instances[0].closed
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "default_profile": "gp",
        "profiles": {
            "patient": {"collection": "patient__nemotron-3-embed-1b", "points": 741},
            "gp": {"collection": "gp__nemotron-3-embed-1b", "points": 364},
        },
    }
    assert FakeClient.instances[0].closed  # released at shutdown (local Qdrant locks its directory)


def test_cors_allows_configured_origins_only(monkeypatch):
    patch_storage(monkeypatch)
    with TestClient(entrypoint.create_app(make_settings())) as client:
        allowed = client.get("/api/health", headers={"Origin": "https://host.test"})
        other = client.get("/api/health", headers={"Origin": "https://evil.test"})
    assert allowed.headers["access-control-allow-origin"] == "https://host.test"
    assert "access-control-allow-origin" not in other.headers


def test_startup_builds_each_profile_from_its_own_settings(monkeypatch):
    patch_storage(monkeypatch)
    with TestClient(entrypoint.create_app(make_settings())) as client:
        services = client.app.state.chat_services
        for profile in ("patient", "gp"):
            assert services[profile]._error_message == load_prompt(profile, "error")
    assert load_prompt("patient", "error") != load_prompt("gp", "error")


def test_startup_warns_when_a_profile_is_not_ingested(monkeypatch, caplog):
    patch_storage(monkeypatch)
    monkeypatch.setitem(POINTS, "gp", 0)
    with caplog.at_level("WARNING"), TestClient(entrypoint.create_app(make_settings())):
        pass
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert warnings == [
        "Profile gp: collection gp__nemotron-3-embed-1b is empty, ingest it before asking questions"
    ]
