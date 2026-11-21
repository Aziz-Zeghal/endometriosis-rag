"""Base class for vector stores."""

import logging
from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings

from endorag_ingestion.core.models import Chunk, ScoredChunk

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Indexes chunks and searches them.

    The store owns its `embedding` (a LangChain `Embeddings`), so documents and queries are
    always embedded by the same model: callers pass text, never vectors.
    """

    embedding: Embeddings

    @abstractmethod
    def add_documents(self, chunks: list[Chunk]) -> list[str]:
        """Embed the chunks and store them. Returns their storage ids."""

    @abstractmethod
    def delete_by_metadata(self, field: str, value: str) -> int:
        """Delete every chunk whose payload `field` equals `value`. Returns the number deleted."""

    @abstractmethod
    def search(self, query: str, k: int) -> list[ScoredChunk]:
        """The `k` chunks that best match the query, best first."""

    def upsert_documents(self, chunks: list[Chunk], key_field: str = "doc_id") -> list[str]:
        """Replace every stored chunk sharing a `key_field` value with the new chunks.

        For each distinct value of `key_field` in `chunks`, the existing chunks with that
        value are deleted before the new ones are added, so re-ingesting a document never
        leaves stale or duplicate chunks.
        """
        for value in {getattr(c, key_field) for c in chunks}:
            deleted = self.delete_by_metadata(key_field, value)
            logger.debug("Deleted %d existing chunks where %s=%r", deleted, key_field, value)
        return self.add_documents(chunks)

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the store. Default: nothing to release."""
