import pytest
from endorag_ingestion.core import BasePipeline
from fakes import (
    FakeChunker,
    FakeConnector,
    FakeConverter,
    InMemoryStore,
    make_entry,
)


@pytest.fixture
def make_pipeline(tmp_path):
    def make(storage=None, failing=None, paragraphs=2):
        return BasePipeline(
            FakeConnector(tmp_path, failing),
            FakeConverter(paragraphs),
            FakeChunker(),
            storage or InMemoryStore(),
        )

    return make


def test_run_ingests_every_enabled_entry(make_pipeline):
    store = InMemoryStore()
    summary = make_pipeline(store).run([make_entry("a"), make_entry("b")])
    assert (summary.ok, summary.failed, summary.skipped) == (2, 0, 0)
    assert len(store.points) == 4


def test_failing_document_does_not_stop_the_run(make_pipeline):
    summary = make_pipeline(failing={"a"}).run([make_entry("a"), make_entry("b")])
    assert (summary.ok, summary.failed) == (1, 1)
    failed = next(r for r in summary.results if r.status == "failed")
    assert failed.doc_id == "a" and "cannot fetch" in failed.error


def test_disabled_entry_is_skipped(make_pipeline):
    summary = make_pipeline().run([make_entry("a", enabled=False)])
    assert summary.skipped == 1


def test_reingestion_leaves_no_stale_chunks(make_pipeline):
    store = InMemoryStore()
    make_pipeline(store, paragraphs=3).run([make_entry("a")])
    make_pipeline(store, paragraphs=1).run([make_entry("a")])
    assert len(store.points) == 1


def test_empty_conversion_fails_the_document(make_pipeline):
    summary = make_pipeline(paragraphs=0).run([make_entry("a")])
    assert summary.failed == 1


def test_close_releases_connector_converter_and_storage(tmp_path):
    closed = []

    class Connector(FakeConnector):
        def close(self):
            closed.append("connector")

    class Converter(FakeConverter):
        def close(self):
            closed.append("converter")

    class Store(InMemoryStore):
        def close(self):
            closed.append("storage")

    BasePipeline(Connector(tmp_path), Converter(), FakeChunker(), Store()).close()
    assert closed == ["connector", "converter", "storage"]


def test_upsert_replaces_only_the_documents_it_receives(make_pipeline, tmp_path):
    store = InMemoryStore()
    make_pipeline(store, paragraphs=2).run([make_entry("a"), make_entry("b")])
    raw = FakeConnector(tmp_path).download(make_entry("a"))
    chunks = FakeChunker().chunk(FakeConverter(1).convert(raw))
    assert store.upsert_documents(chunks) == [chunks[0].point_id]
    assert sorted(c.doc_id for c, _ in store.points.values()) == ["a", "b", "b"]
