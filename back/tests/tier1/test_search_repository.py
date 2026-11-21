from datetime import date

from endorag_back.config.settings import Settings
from endorag_back.repositories.search_repository import (
    SearchRepository,
    cap_per_document,
    remove_near_duplicates,
)
from endorag_ingestion.core import Chunk, ScoredChunk

BOX = "Une ALD dite « hors liste » ou ALD 31 est une maladie grave qui n'est pas dans la liste."


def hit(
    doc_id: str,
    index: int = 0,
    text: str | None = None,
    dense: float = 0.6,
    published: date = date(2025, 1, 1),
) -> ScoredChunk:
    chunk = Chunk(
        doc_id=doc_id,
        chunk_index=index,
        text=text or f"Texte propre au document {doc_id}, passage numéro {index}.",
        source="Example",
        title=doc_id,
        url=f"https://example.org/{doc_id}",
        published=published,
        retrieved=date(2026, 11, 21),
        audience="patient",
        licence="all-rights-reserved",
        format="html",
    )
    return ScoredChunk(chunk=chunk, score=0.01, dense_score=dense)


def ids(hits: list[ScoredChunk]) -> list[tuple[str, int]]:
    return [(h.chunk.doc_id, h.chunk.chunk_index) for h in hits]


class FakeStore:
    def __init__(self, hits: list[ScoredChunk]) -> None:
        self.hits = hits
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        self.calls.append((query, k))
        return self.hits[:k]


def make_settings(**kw) -> Settings:
    return Settings(
        _env_file=None,
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
        **kw,
    )


def test_identical_box_on_several_pages_is_kept_once_at_the_best_rank_most_recent_copy():
    hits = [
        hit("ameli-traitement", 12, BOX, published=date(2025, 3, 1)),
        hit("has-diagnostic"),
        hit("ameli-definition", 7, "  " + BOX.upper() + "\n", published=date(2026, 4, 9)),
        hit("ameli-symptomes", 27, BOX, published=date(2024, 1, 1)),
    ]
    kept = remove_near_duplicates(hits, threshold=0.95)
    assert ids(kept) == [("ameli-definition", 7), ("has-diagnostic", 0)]


def test_near_duplicate_with_reordered_words_is_removed_but_distinct_passages_stay():
    a = "Pas de cœlioscopie dans le seul but de confirmer le diagnostic si l'imagerie est typique."
    b = "Si l'imagerie est typique, pas de cœlioscopie dans le seul but de confirmer le diagnostic."
    hits = [hit("fiche", 0, a), hit("messages", 0, b), hit("fiche", 1)]
    assert ids(remove_near_duplicates(hits, threshold=0.95)) == [("fiche", 0), ("fiche", 1)]


def test_per_document_cap_keeps_the_best_ranked_chunks_of_each_document():
    hits = [hit("a", 0), hit("a", 1), hit("b", 0), hit("a", 2), hit("b", 1), hit("b", 2)]
    assert ids(cap_per_document(hits, cap=2)) == [("a", 0), ("a", 1), ("b", 0), ("b", 1)]


def test_retrieve_searches_candidates_then_dedups_caps_and_cuts_to_top_k():
    store = FakeStore(
        [hit("a", 0, BOX), hit("a", 1), hit("b", 0, BOX), hit("a", 2), hit("c", 0), hit("d", 0)]
    )
    settings = make_settings(retrieve_candidates=6, max_chunks_per_doc=2, retrieve_top_k=3)
    result = SearchRepository(store, settings).retrieve("ALD 31")
    assert store.calls == [("ALD 31", 6)]
    assert ids(result.chunks) == [("a", 0), ("a", 1), ("c", 0)]


def test_verdict_uses_the_best_dense_score_against_the_threshold():
    settings = make_settings(min_dense_score=0.45)
    weak = SearchRepository(FakeStore([hit("a", dense=0.29), hit("b", dense=0.44)]), settings)
    strong = SearchRepository(FakeStore([hit("a", dense=0.30), hit("b", dense=0.45)]), settings)

    weak_result, strong_result = weak.retrieve("q"), strong.retrieve("q")
    assert (weak_result.best_dense_score, weak_result.sufficient) == (0.44, False)
    assert (strong_result.best_dense_score, strong_result.sufficient) == (0.45, True)


def test_no_hit_is_insufficient_evidence():
    result = SearchRepository(FakeStore([]), make_settings()).retrieve("q")
    assert result.chunks == []
    assert not result.sufficient


def test_reranker_sees_deduped_capped_candidates_and_its_order_is_kept():
    seen = []

    class Reverse:
        def rerank(self, query, chunks):
            seen.append((query, ids(chunks)))
            return chunks[::-1]

    store = FakeStore([hit("a", 0), hit("a", 1), hit("a", 2), hit("b", 0), hit("c", 0)])
    settings = make_settings(max_chunks_per_doc=2, retrieve_top_k=2)
    result = SearchRepository(store, settings, reranker=Reverse()).retrieve("q")
    assert seen == [("q", [("a", 0), ("a", 1), ("b", 0), ("c", 0)])]
    assert ids(result.chunks) == [("c", 0), ("b", 0)]


def test_more_recent_duplicate_keeps_the_dense_score_that_earned_the_rank():
    old = hit("old", 0, BOX, dense=0.9, published=date(2020, 1, 1))
    new = hit("new", 0, BOX, dense=0.3, published=date(2026, 1, 1))
    result = SearchRepository(FakeStore([old, new]), make_settings()).retrieve("q")
    assert ids(result.chunks) == [("new", 0)]
    assert (result.best_dense_score, result.sufficient) == (0.9, True)
