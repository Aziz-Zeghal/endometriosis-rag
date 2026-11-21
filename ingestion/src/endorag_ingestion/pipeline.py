"""Template method: fetch -> convert -> chunk -> embed -> upsert, one document at a time."""

import logging

from endorag_ingestion.core import (
    Chunk,
    Chunker,
    Connector,
    ConvertedDocument,
    Converter,
    DocumentResult,
    Embedder,
    ManifestEntry,
    RawDocument,
    RunSummary,
    VectorStore,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Owns the sequence and the error handling. Steps are injected strategies.

    A document that fails at any step is recorded and skipped; the run continues.
    Before upserting, the document's existing points are deleted, so re-running never
    leaves stale or duplicate chunks.
    """

    def __init__(
        self,
        connector: Connector,
        converter: Converter,
        chunker: Chunker,
        embedder: Embedder,
        store: VectorStore,
    ) -> None:
        self.connector = connector
        self.converter = converter
        self.chunker = chunker
        self.embedder = embedder
        self.store = store

    def run(self, entries: list[ManifestEntry]) -> RunSummary:
        summary = RunSummary()
        for entry in entries:
            if not entry.enabled:
                summary.results.append(DocumentResult(doc_id=entry.id, status="skipped"))
                continue
            try:
                n = self.process(entry)
            except Exception as exc:
                logger.exception("Failed to ingest %s", entry.id)
                summary.results.append(
                    DocumentResult(doc_id=entry.id, status="failed", error=repr(exc))
                )
            else:
                logger.info("Ingested %s (%d chunks)", entry.id, n)
                summary.results.append(DocumentResult(doc_id=entry.id, status="ok", chunks=n))
        return summary

    def process(self, entry: ManifestEntry) -> int:
        raw = self.fetch(entry)
        doc = self.convert(raw)
        chunks = self.chunk(doc)
        if not chunks:
            raise ValueError(f"{entry.id}: conversion produced no chunks")
        vectors = self.embed(chunks)
        return self.store_chunks(entry.id, chunks, vectors)

    # Steps, overridable one by one.
    def fetch(self, entry: ManifestEntry) -> RawDocument:
        return self.connector.fetch(entry)

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        return self.converter.convert(raw)

    def chunk(self, doc: ConvertedDocument) -> list[Chunk]:
        return self.chunker.chunk(doc)

    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        return self.embedder.embed_documents([c.embedding_text for c in chunks])

    def store_chunks(self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        self.store.delete_by_doc_id(doc_id)
        return self.store.upsert(chunks, vectors)
