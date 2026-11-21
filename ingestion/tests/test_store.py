"""QdrantStore on an in-memory Qdrant client with tiny fake dense vectors.

BM25 needs the fastembed `Qdrant/bm25` files, downloaded once into CACHE_DIR; the tests
are skipped if they are neither cached nor downloadable.
"""

from datetime import date

import pytest
from endorag_ingestion.core import Chunk
from endorag_ingestion.pipeline import Pipeline
from endorag_ingestion.stores import QdrantStore
from endorag_ingestion.stores import qdrant as qdrant_module
from qdrant_client import QdrantClient

TEXTS = {
    ("ameli-traitement", 0): "Le diénogest est un progestatif utilisé dans l'endométriose.",
    ("ameli-traitement", 1): "La chirurgie est discutée en cas d'échec du traitement hormonal.",
    ("has-diagnostic", 0): "L'échographie pelvienne est l'examen de première intention.",
    ("has-diagnostic", 1): "L'IRM pelvienne précise l'extension des lésions profondes.",
}
FLAT = [1.0, 1.0, 1.0]  # uninformative dense vector


def make_chunk(doc_id: str, index: int, text: str) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        chunk_index=index,
        text=text,
        heading_path=["Endométriose"],
        source="Example",
        title=f"Title {doc_id}",
        url=f"https://example.org/{doc_id}",
        published=date(2026, 1, 1),
        retrieved=date(2026, 11, 21),
        audience="patient",
        licence="all-rights-reserved",
        format="html",
    )


CHUNKS = [make_chunk(d, i, t) for (d, i), t in TEXTS.items()]


@pytest.fixture
def store():
    s = QdrantStore("test", dimension=3, client=QdrantClient(":memory:"))
    try:
        _ = s.bm25
    except RuntimeError as exc:
        pytest.skip(str(exc))
    yield s
    s.close()


def one_hot(i: int) -> list[float]:
    return [1.0 if j == i % 3 else 0.0 for j in range(3)]


def test_upsert_then_search_returns_the_matching_chunk(store):
    store.upsert(CHUNKS, [one_hot(i) for i in range(len(CHUNKS))])
    hits = store.search("IRM pelvienne lésions profondes", one_hot(3), limit=2)
    assert hits[0].chunk == CHUNKS[3]


def test_exact_term_wins_through_bm25_with_flat_dense_vectors(store):
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    hits = store.search("diénogest", FLAT, limit=5)
    assert hits[0].chunk.doc_id == "ameli-traitement"
    assert hits[0].chunk.chunk_index == 0


def test_exact_term_matches_when_typed_without_accents(store):
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    hits = store.search("dienogest", FLAT, limit=5)
    assert hits[0].chunk == CHUNKS[0]
    assert hits[0].chunk.text.startswith("Le diénogest")  # payload keeps its accents


def test_bm25_stems_french_words(store):
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    hits = store.search("traitements hormonaux", FLAT, limit=5)
    assert hits[0].chunk == CHUNKS[1]


def test_delete_by_doc_id_removes_only_that_document(store):
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    store.delete_by_doc_id("ameli-traitement")
    assert store.count() == 2
    assert store.chunk_counts() == {"has-diagnostic": 2}


def test_reupsert_is_idempotent(store):
    assert store.upsert(CHUNKS, [FLAT] * len(CHUNKS)) == 4
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    assert store.count() == 4
    assert store.chunk_counts() == {"ameli-traitement": 2, "has-diagnostic": 2}


def test_reingesting_with_fewer_chunks_leaves_no_stale_points(store):
    pipeline = Pipeline(None, None, None, None, store)
    pipeline.store_chunks("ameli-traitement", CHUNKS, [FLAT] * len(CHUNKS))
    pipeline.store_chunks("ameli-traitement", CHUNKS[:1], [FLAT])
    assert store.count() == 3
    assert [h.chunk for h in store.search("chirurgie", FLAT, limit=10)].count(CHUNKS[1]) == 0


def test_payload_round_trips_to_chunk(store):
    store.upsert(CHUNKS, [one_hot(i) for i in range(len(CHUNKS))])
    found = [h.chunk for h in store.search("endométriose", FLAT, limit=10)]
    assert sorted(found, key=lambda c: c.point_id) == sorted(CHUNKS, key=lambda c: c.point_id)


def test_upsert_in_several_batches(store):
    store.batch_size = 3
    store.upsert(CHUNKS, [FLAT] * len(CHUNKS))
    assert store.count() == 4


def test_mismatched_vectors_are_rejected(store):
    with pytest.raises(ValueError):
        store.upsert(CHUNKS, [FLAT])


def test_reopening_with_another_dimension_fails_early():
    client = QdrantClient(":memory:")
    QdrantStore("test", dimension=3, client=client)
    with pytest.raises(ValueError, match="dimension"):
        QdrantStore("test", dimension=5, client=client)


def test_bm25_load_error_keeps_the_original_cause(monkeypatch):
    def broken(*args, **kwargs):
        raise TypeError("unexpected keyword 'language'")

    monkeypatch.setattr(qdrant_module, "SparseTextEmbedding", broken)
    s = QdrantStore("test", dimension=3, client=QdrantClient(":memory:"))
    with pytest.raises(RuntimeError, match="unexpected keyword 'language'"):
        _ = s.bm25


def test_local_path_mode_persists(tmp_path):
    s = QdrantStore("test", dimension=3, path=tmp_path)
    try:
        s.upsert(CHUNKS[:1], [FLAT])
    except RuntimeError as exc:
        pytest.skip(str(exc))
    finally:
        s.close()
    s = QdrantStore("test", dimension=3, path=tmp_path)
    assert s.count() == 1
    s.close()
