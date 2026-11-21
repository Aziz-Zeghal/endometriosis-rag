"""QdrantStore on an in-memory Qdrant client with tiny fake dense vectors.

BM25 needs the fastembed `Qdrant/bm25` files, downloaded once into CACHE_DIR; the tests
are skipped if they are neither cached nor downloadable.
"""

from datetime import date

import pytest
from endorag_ingestion.core import Chunk
from endorag_ingestion.vector_storage import QdrantStore
from endorag_ingestion.vector_storage import qdrant as qdrant_module
from langchain_core.embeddings import Embeddings
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


def one_hot(i: int) -> list[float]:
    return [1.0 if j == i % 3 else 0.0 for j in range(3)]


class LookupEmbedder(Embeddings):
    """Dense vectors looked up by text (FLAT by default), so tests control the dense side."""

    name = "lookup"

    def __init__(self, vectors: dict[str, list[float]] | None = None, dim: int = 3) -> None:
        self.vectors = vectors or {}
        self.dim = dim

    @property
    def dimension(self) -> int:
        return self.dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.vectors.get(text, FLAT)


ONE_HOT = LookupEmbedder(
    {c.embedding_text: one_hot(i) for i, c in enumerate(CHUNKS)}
    | {"IRM pelvienne lésions profondes": one_hot(3)}
)


def make_store(embedding: Embeddings | None = None, **kw) -> QdrantStore:
    if "path" not in kw:
        kw["client"] = QdrantClient(":memory:")
    return QdrantStore("test", embedding or LookupEmbedder(), **kw)


@pytest.fixture
def store():
    s = make_store()
    try:
        _ = s.bm25
    except RuntimeError as exc:
        pytest.skip(str(exc))
    yield s
    s.close()


def test_add_then_search_returns_the_matching_chunk(store):
    store.embedding = ONE_HOT
    store.add_documents(CHUNKS)
    hits = store.search("IRM pelvienne lésions profondes", k=2)
    assert hits[0].chunk == CHUNKS[3]


def test_exact_term_wins_through_bm25_with_flat_dense_vectors(store):
    store.add_documents(CHUNKS)
    hits = store.search("diénogest", k=5)
    assert hits[0].chunk.doc_id == "ameli-traitement"
    assert hits[0].chunk.chunk_index == 0


def test_exact_term_matches_when_typed_without_accents(store):
    store.add_documents(CHUNKS)
    hits = store.search("dienogest", k=5)
    assert hits[0].chunk == CHUNKS[0]
    assert hits[0].chunk.text.startswith("Le diénogest")  # payload keeps its accents


def test_bm25_stems_french_words(store):
    store.add_documents(CHUNKS)
    hits = store.search("traitements hormonaux", k=5)
    assert hits[0].chunk == CHUNKS[1]


def test_delete_by_metadata_removes_only_that_document(store):
    store.add_documents(CHUNKS)
    assert store.delete_by_metadata("doc_id", "ameli-traitement") == 2
    assert store.delete_by_metadata("doc_id", "ameli-traitement") == 0
    assert store.count() == 2
    assert store.chunk_counts() == {"has-diagnostic": 2}


def test_readding_is_idempotent(store):
    assert store.add_documents(CHUNKS) == [c.point_id for c in CHUNKS]
    store.add_documents(CHUNKS)
    assert store.count() == 4
    assert store.chunk_counts() == {"ameli-traitement": 2, "has-diagnostic": 2}


def test_upserting_fewer_chunks_leaves_no_stale_points(store):
    store.upsert_documents(CHUNKS)
    store.upsert_documents(CHUNKS[:1])
    assert store.count() == 3
    assert [h.chunk for h in store.search("chirurgie", k=10)].count(CHUNKS[1]) == 0


def test_payload_round_trips_to_chunk(store):
    store.embedding = ONE_HOT
    store.add_documents(CHUNKS)
    found = [h.chunk for h in store.search("endométriose", k=10)]
    assert sorted(found, key=lambda c: c.point_id) == sorted(CHUNKS, key=lambda c: c.point_id)


def test_add_in_several_batches(store):
    store.batch_size = 3
    store.add_documents(CHUNKS)
    assert store.count() == 4


def test_mismatched_vectors_are_rejected(store):
    class Broken(LookupEmbedder):
        def embed_documents(self, texts):
            return [FLAT]

    store.embedding = Broken()
    with pytest.raises(ValueError):
        store.add_documents(CHUNKS)


def test_search_embeds_the_query_with_the_store_embedder(store):
    seen = []

    class Spy(LookupEmbedder):
        def embed_query(self, text):
            seen.append(text)
            return FLAT

    store.embedding = Spy()
    store.add_documents(CHUNKS)
    seen.clear()  # add_documents() embedded the documents through the same embedder
    store.search("chirurgie", k=1)
    assert seen == ["chirurgie"]


def test_reopening_with_another_dimension_fails_early():
    client = QdrantClient(":memory:")
    QdrantStore("test", LookupEmbedder(dim=3), client=client)
    with pytest.raises(ValueError, match="dimension"):
        QdrantStore("test", LookupEmbedder(dim=5), client=client)


def test_bm25_load_error_keeps_the_original_cause(monkeypatch):
    def broken(*args, **kwargs):
        raise TypeError("unexpected keyword 'language'")

    monkeypatch.setattr(qdrant_module, "SparseTextEmbedding", broken)
    s = make_store()
    with pytest.raises(RuntimeError, match="unexpected keyword 'language'"):
        _ = s.bm25


def test_local_path_mode_persists(tmp_path):
    s = make_store(path=tmp_path)
    try:
        s.add_documents(CHUNKS[:1])
    except RuntimeError as exc:
        pytest.skip(str(exc))
    finally:
        s.close()
    s = make_store(path=tmp_path)
    assert s.count() == 1
    s.close()


def test_dimension_is_probed_for_an_embedding_without_one():
    class Plain(Embeddings):
        def embed_documents(self, texts):
            return [FLAT for _ in texts]

        def embed_query(self, text):
            return FLAT

    store = QdrantStore("test", Plain(), client=QdrantClient(":memory:"))
    params = store.client.get_collection("test").config.params
    assert params.vectors[qdrant_module.DENSE].size == 3
