"""Read-only retrieval over the ingestion `QdrantStore`.

Hybrid candidates → near-duplicate removal → per-document cap → (rerank) → top k, plus an
evidence verdict from the raw dense similarity (the fused RRF score is rank-based, so it
cannot tell "not in the corpus" apart).
"""

import logging
import re

from endorag_ingestion.core import ScoredChunk
from endorag_ingestion.vector_storage import QdrantStore
from endorag_ingestion.vector_storage.qdrant import fold_accents
from pydantic import BaseModel

from endorag_back.config.settings import Settings
from endorag_back.services.reranker import NoReranker, Reranker

logger = logging.getLogger(__name__)


class Retrieval(BaseModel):
    chunks: list[ScoredChunk]  # best first, at most `retrieve_top_k`
    best_dense_score: float  # highest dense cosine similarity among `chunks` (0 if none)
    sufficient: bool  # best_dense_score >= min_dense_score


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", fold_accents(text).lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def remove_near_duplicates(chunks: list[ScoredChunk], threshold: float) -> list[ScoredChunk]:
    """Drop chunks whose word set overlaps a better-ranked one by `threshold` or more (Jaccard).

    The same box repeated on several pages or sites is kept once, at the best rank, from the
    most recently published copy, with the highest dense score of the group (copies embed
    different heading paths, so the evidence verdict must not drop with the swap).
    """
    kept: list[tuple[set[str], ScoredChunk]] = []
    for hit in chunks:
        words = _words(hit.chunk.text)
        for i, (other_words, other) in enumerate(kept):
            if _jaccard(words, other_words) >= threshold:
                if hit.chunk.published > other.chunk.published:
                    dense = max(hit.dense_score or 0.0, other.dense_score or 0.0)
                    kept[i] = (other_words, hit.model_copy(update={"dense_score": dense}))
                break
        else:
            kept.append((words, hit))
    return [hit for _, hit in kept]


def cap_per_document(chunks: list[ScoredChunk], cap: int) -> list[ScoredChunk]:
    """Keep at most `cap` chunks per document, in order, so one source cannot fill the top k."""
    counts: dict[str, int] = {}
    kept = []
    for hit in chunks:
        counts[hit.chunk.doc_id] = counts.get(hit.chunk.doc_id, 0) + 1
        if counts[hit.chunk.doc_id] <= cap:
            kept.append(hit)
    return kept


class SearchRepository:
    def __init__(
        self, store: QdrantStore, settings: Settings, reranker: Reranker | None = None
    ) -> None:
        self._store = store
        self._settings = settings
        self._reranker = reranker or NoReranker()

    def retrieve(self, query: str) -> Retrieval:
        s = self._settings
        candidates = self._store.search(query, k=s.retrieve_candidates)
        chunks = remove_near_duplicates(candidates, s.dedup_similarity)
        chunks = cap_per_document(chunks, s.max_chunks_per_doc)
        chunks = self._reranker.rerank(query, chunks)[: s.retrieve_top_k]
        best = max((c.dense_score or 0.0 for c in chunks), default=0.0)
        logger.debug(
            "%d candidates -> %d chunks, best dense %.3f", len(candidates), len(chunks), best
        )
        return Retrieval(chunks=chunks, best_dense_score=best, sufficient=best >= s.min_dense_score)
