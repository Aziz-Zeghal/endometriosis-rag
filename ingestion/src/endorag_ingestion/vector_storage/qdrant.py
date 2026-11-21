"""Qdrant vector store (local mode) with hybrid dense + BM25 search fused by RRF.

Each hit also carries its raw dense cosine similarity, since RRF scores are rank-based.
"""

import math
import unicodedata
from pathlib import Path

from fastembed import SparseEmbedding, SparseTextEmbedding
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient, models

from endorag_ingestion.core import BaseVectorStore, Chunk, ScoredChunk
from endorag_ingestion.core.settings import CACHE_DIR

DENSE = "dense"
SPARSE = "bm25"
BM25_MODEL = "Qdrant/bm25"
BM25_LANGUAGE = "french"  # Snowball stemmer + French stopwords bundled with the model
PAYLOAD_INDEXES = ("doc_id", "audience", "source")


def fold_accents(text: str) -> str:
    """'diénogest' -> 'dienogest', so BM25 matches queries typed without accents."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _dimension(embedding: Embeddings) -> int:
    """`embedding.dimension` when the embedding has one (ours do), else probed once."""
    return getattr(embedding, "dimension", None) or len(embedding.embed_query("dimension"))


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.hypot(*a) * math.hypot(*b)
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0


class QdrantStore(BaseVectorStore):
    """Stores chunks with a dense vector (from its embedding) and a BM25 sparse vector.

    Local mode locks its directory: only one client per path at a time, so call `close()`.
    Pass `client` (e.g. `QdrantClient(":memory:")`) instead of `path` in tests.
    """

    def __init__(
        self,
        collection: str,
        embedding: Embeddings,
        path: Path | None = None,
        client: QdrantClient | None = None,
        batch_size: int = 128,
    ) -> None:
        if (path is None) == (client is None):
            raise ValueError("pass exactly one of 'path' or 'client'")
        self.client = client or QdrantClient(path=str(path))
        self.collection = collection
        self.embedding = embedding
        self.batch_size = batch_size
        self._bm25: SparseTextEmbedding | None = None
        self._ensure_collection(_dimension(embedding))

    def _ensure_collection(self, dimension: int) -> None:
        if self.client.collection_exists(self.collection):
            params = self.client.get_collection(self.collection).config.params
            existing = params.vectors[DENSE].size
            if existing != dimension:
                raise ValueError(
                    f"collection {self.collection!r} has dense dimension {existing}, "
                    f"not {dimension}"
                )
            return
        self.client.create_collection(
            self.collection,
            vectors_config={
                DENSE: models.VectorParams(size=dimension, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
        for field in PAYLOAD_INDEXES:
            self.client.create_payload_index(
                self.collection, field, field_schema=models.PayloadSchemaType.KEYWORD
            )

    @property
    def bm25(self) -> SparseTextEmbedding:
        """Loaded on first use; the model files are downloaded once into CACHE_DIR."""
        if self._bm25 is None:
            try:
                self._bm25 = SparseTextEmbedding(
                    BM25_MODEL, cache_dir=str(CACHE_DIR / "fastembed"), language=BM25_LANGUAGE
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Cannot load the {BM25_MODEL} sparse model (cache: "
                    f"{CACHE_DIR / 'fastembed'}): {exc!r}"
                ) from exc
        return self._bm25

    @staticmethod
    def _sparse(embedding: SparseEmbedding) -> models.SparseVector:
        return models.SparseVector(
            indices=embedding.indices.tolist(), values=embedding.values.tolist()
        )

    def add_documents(self, chunks: list[Chunk]) -> list[str]:
        vectors = self.embedding.embed_documents([c.embedding_text for c in chunks])
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start : start + self.batch_size]
            sparse = self.bm25.embed([fold_accents(c.embedding_text) for c in batch])
            points = [
                models.PointStruct(
                    id=chunk.point_id,
                    vector={DENSE: dense, SPARSE: self._sparse(sp)},
                    payload=chunk.model_dump(mode="json"),
                )
                for chunk, dense, sp in zip(
                    batch, vectors[start : start + self.batch_size], sparse, strict=True
                )
            ]
            self.client.upsert(self.collection, points=points)
        return [c.point_id for c in chunks]

    def delete_by_metadata(self, field: str, value: str) -> int:
        selector = models.Filter(
            must=[models.FieldCondition(key=field, match=models.MatchValue(value=value))]
        )
        deleted = self.client.count(self.collection, count_filter=selector, exact=True).count
        if deleted:
            self.client.delete(
                self.collection, points_selector=models.FilterSelector(filter=selector)
            )
        return deleted

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        query_vector = self.embedding.embed_query(query)
        sparse = self._sparse(next(iter(self.bm25.query_embed(fold_accents(query)))))
        response = self.client.query_points(
            self.collection,
            prefetch=[
                models.Prefetch(query=query_vector, using=DENSE, limit=k * 4),
                models.Prefetch(query=sparse, using=SPARSE, limit=k * 4),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k,
            with_payload=True,
            with_vectors=[DENSE],
        )
        return [
            ScoredChunk(
                chunk=Chunk.model_validate(p.payload),
                score=p.score,
                dense_score=_cosine(query_vector, p.vector[DENSE]),
            )
            for p in response.points
        ]

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def chunk_counts(self) -> dict[str, int]:
        """Number of points per doc id, sorted by doc id (for stats)."""
        counts: dict[str, int] = {}
        offset = None
        while True:
            points, offset = self.client.scroll(
                self.collection, limit=1000, offset=offset, with_payload=["doc_id"]
            )
            for p in points:
                counts[p.payload["doc_id"]] = counts.get(p.payload["doc_id"], 0) + 1
            if offset is None:
                return dict(sorted(counts.items()))

    def close(self) -> None:
        self.client.close()
