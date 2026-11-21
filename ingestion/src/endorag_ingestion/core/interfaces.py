"""Strategy interfaces: one abstract class per pipeline step."""

from abc import ABC, abstractmethod

from endorag_ingestion.core.models import (
    Chunk,
    ConvertedDocument,
    ManifestEntry,
    RawDocument,
    ScoredChunk,
)


class Connector(ABC):
    """Fetches a manifest entry and caches the raw bytes on disk."""

    @abstractmethod
    def fetch(self, entry: ManifestEntry) -> RawDocument: ...


class Converter(ABC):
    """Turns a raw file into Markdown with its headings preserved."""

    @abstractmethod
    def convert(self, raw: RawDocument) -> ConvertedDocument: ...


class Chunker(ABC):
    """Splits a converted document into retrievable chunks."""

    @abstractmethod
    def chunk(self, doc: ConvertedDocument) -> list[Chunk]: ...


class Embedder(ABC):
    """Dense embeddings. Queries and passages are separate: some models prefix them differently."""

    name: str

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class VectorStore(ABC):
    """Stores chunks with their vectors and searches them."""

    @abstractmethod
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> int: ...

    @abstractmethod
    def delete_by_doc_id(self, doc_id: str) -> None: ...

    @abstractmethod
    def search(self, query: str, query_vector: list[float], limit: int) -> list[ScoredChunk]: ...
