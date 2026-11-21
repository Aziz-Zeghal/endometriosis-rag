"""Reranking hook: a research point, so a small protocol with a no-op default.

A reranker (cross-encoder, managed reranker) is plugged in only if the evaluation shows a
gain over the hybrid search order.
"""

from typing import Protocol

from endorag_ingestion.core import ScoredChunk


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        """The chunks reordered by relevance to the query, best first."""
        ...


class NoReranker:
    """Keeps the hybrid search order."""

    def rerank(self, query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        return chunks
