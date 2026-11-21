import threading

import httpx
import openai
import pytest
from endorag_ingestion.core.settings import Settings
from endorag_ingestion.embedder import OpenAICompatibleEmbedder, openai_compatible
from endorag_ingestion.factory import build_storage


def transient_error() -> Exception:
    return openai.APIConnectionError(request=httpx.Request("POST", "http://test/embeddings"))


class FakeClient:
    """Stands in for OpenAIEmbeddings; fails on the calls listed in `fail_on` (1-based)."""

    def __init__(self, fail_on: set[int] | None = None, error=transient_error) -> None:
        self.calls: list[list[str]] = []
        self.fail_on = fail_on or set()
        self.error = error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if len(self.calls) in self.fail_on:
            raise self.error()
        return [[float(len(t)), 0.5, 1.0] for t in texts]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(openai_compatible.time, "sleep", sleeps.append)
    return sleeps


def make(tmp_path, client, model="nemotron-3-embed-1b"):
    return OpenAICompatibleEmbedder(model, cache_path=tmp_path / "cache.sqlite", client=client)


TEXTS = [f"L'endométriose, passage numéro {i}." for i in range(40)]


def test_batches_of_16(tmp_path):
    client = FakeClient()
    vectors = make(tmp_path, client).embed_documents(TEXTS)
    assert [len(c) for c in client.calls] == [16, 16, 8]
    assert vectors[3] == [float(len(TEXTS[3])), 0.5, 1.0]


def test_cache_hit_avoids_the_client(tmp_path):
    make(tmp_path, FakeClient()).embed_documents(TEXTS[:3])
    client = FakeClient()
    embedder = make(tmp_path, client)  # new instance, same cache file
    assert embedder.embed_documents(TEXTS[:3])[0] == [float(len(TEXTS[0])), 0.5, 1.0]
    assert embedder.embed_query(TEXTS[1]) == [float(len(TEXTS[1])), 0.5, 1.0]
    assert client.calls == []


def test_retry_succeeds_after_two_transient_failures(tmp_path, no_sleep):
    client = FakeClient(fail_on={1, 2})
    vectors = make(tmp_path, client).embed_documents(TEXTS[:2])
    assert len(vectors) == 2
    assert len(client.calls) == 3
    assert no_sleep == [2.0, 4.0]


def test_non_transient_error_is_not_retried(tmp_path):
    client = FakeClient(fail_on={1}, error=lambda: ValueError("bad input"))
    with pytest.raises(ValueError):
        make(tmp_path, client).embed_documents(TEXTS[:2])
    assert len(client.calls) == 1


def test_resume_after_failure_mid_run(tmp_path):
    # Batch 2 fails on every attempt: the run aborts but batch 1 is already cached.
    failing = FakeClient(fail_on=set(range(2, 2 + openai_compatible.MAX_ATTEMPTS)))
    with pytest.raises(openai.APIConnectionError):
        make(tmp_path, failing).embed_documents(TEXTS)

    client = FakeClient()
    vectors = make(tmp_path, client).embed_documents(TEXTS)
    assert len(vectors) == 40
    assert [len(c) for c in client.calls] == [16, 8]
    assert TEXTS[0] not in client.calls[0]


def test_usable_from_another_thread(tmp_path):
    # The backend builds the embedder at startup and calls it from a worker thread.
    embedder = make(tmp_path, FakeClient())
    embedder.embed_query(TEXTS[0])
    results: list = []
    thread = threading.Thread(
        target=lambda: results.extend([embedder.embed_query(TEXTS[0]), embedder.embed_query("x")])
    )
    thread.start()
    thread.join()
    assert results == [[float(len(TEXTS[0])), 0.5, 1.0], [1.0, 0.5, 1.0]]


def test_dimension_known_or_probed_once(tmp_path):
    assert make(tmp_path, FakeClient()).dimension == 2048
    client = FakeClient()
    embedder = make(tmp_path, client, model="some-other-model")
    assert embedder.dimension == 3
    assert embedder.dimension == 3
    assert len(client.calls) == 1


def test_factory_builds_the_embedder_from_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(openai_compatible, "CACHE_DIR", tmp_path)
    settings = Settings(
        _env_file=None,
        embedder="gemini-embedding-001",
        qdrant_path=tmp_path / "qdrant",
        llm_base_url="http://test/v1",
        llm_api_key="fake",
    )
    store = build_storage(settings)
    try:
        assert isinstance(store.embedding, OpenAICompatibleEmbedder)
        assert store.embedding.name == "gemini-embedding-001"
        assert store.embedding.dimension == 3072
        assert (tmp_path / "embeddings" / "gemini-embedding-001.sqlite").exists()
    finally:
        store.close()


@pytest.mark.parametrize(
    "missing",
    [{"llm_base_url": None}, {"llm_api_key": None}, {"llm_base_url": None, "llm_api_key": None}],
)
def test_factory_requires_endpoint_settings(missing):
    values = {"llm_base_url": "http://test/v1", "llm_api_key": "fake"} | missing
    with pytest.raises(ValueError, match="LLM_BASE_URL and LLM_API_KEY"):
        build_storage(Settings(_env_file=None, embedder="nemotron-3-embed-1b", **values))


@pytest.mark.live
def test_live_endpoint_dimension(tmp_path, monkeypatch):
    monkeypatch.setattr(openai_compatible, "CACHE_DIR", tmp_path)
    settings = Settings(embedder="nemotron-3-embed-1b")
    embedder = OpenAICompatibleEmbedder(
        settings.embedder, settings.llm_base_url, settings.llm_api_key.get_secret_value()
    )
    vectors = embedder.embed_documents(
        [
            "L'endométriose touche environ une femme sur dix.",
            "Les douleurs pelviennes sont fréquentes.",
        ]
    )
    assert [len(v) for v in vectors] == [2048, 2048]
