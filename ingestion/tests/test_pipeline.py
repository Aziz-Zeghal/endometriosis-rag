from endorag_ingestion.pipeline import Pipeline
from fakes import (
    FakeChunker,
    FakeConnector,
    FakeConverter,
    InMemoryStore,
    make_entry,
)


def make_pipeline(store=None, failing=None, paragraphs=2):
    return Pipeline(
        FakeConnector(failing),
        FakeConverter(paragraphs),
        FakeChunker(),
        store or InMemoryStore(),
    )


def test_run_ingests_every_enabled_entry():
    store = InMemoryStore()
    summary = make_pipeline(store).run([make_entry("a"), make_entry("b")])
    assert (summary.ok, summary.failed, summary.skipped) == (2, 0, 0)
    assert len(store.points) == 4


def test_failing_document_does_not_stop_the_run():
    summary = make_pipeline(failing={"a"}).run([make_entry("a"), make_entry("b")])
    assert (summary.ok, summary.failed) == (1, 1)
    failed = next(r for r in summary.results if r.status == "failed")
    assert failed.doc_id == "a" and "cannot fetch" in failed.error


def test_disabled_entry_is_skipped():
    summary = make_pipeline().run([make_entry("a", enabled=False)])
    assert summary.skipped == 1


def test_reingestion_leaves_no_stale_chunks():
    store = InMemoryStore()
    make_pipeline(store, paragraphs=3).run([make_entry("a")])
    make_pipeline(store, paragraphs=1).run([make_entry("a")])
    assert len(store.points) == 1


def test_empty_conversion_fails_the_document():
    summary = make_pipeline(paragraphs=0).run([make_entry("a")])
    assert summary.failed == 1
