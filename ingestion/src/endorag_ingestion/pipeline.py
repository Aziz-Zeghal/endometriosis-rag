"""Template method: fetch -> convert -> chunk -> index, one document at a time."""

import logging

from endorag_ingestion.core import (
    Chunk,
    Chunker,
    Connector,
    ConvertedDocument,
    Converter,
    DocumentResult,
    ManifestEntry,
    RawDocument,
    RunSummary,
    VectorStore,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Owns the sequence and the error handling. Steps are injected strategies.

    A document that fails at any step is recorded and skipped; the run continues.
    Before indexing, the document's existing points are deleted, so re-running never
    leaves stale or duplicate chunks.
    """

    def __init__(
        self,
        connector: Connector,
        converter: Converter,
        chunker: Chunker,
        store: VectorStore,
    ) -> None:
        self.connector = connector
        self.converter = converter
        self.chunker = chunker
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
        return self.index(entry.id, chunks)

    # Steps, overridable one by one.
    def fetch(self, entry: ManifestEntry) -> RawDocument:
        return self.connector.fetch(entry)

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        return self.converter.convert(raw)

    def chunk(self, doc: ConvertedDocument) -> list[Chunk]:
        return self.chunker.chunk(doc)

    def index(self, doc_id: str, chunks: list[Chunk]) -> int:
        """Replace the document's chunks in the store (which embeds them)."""
        self.store.delete_by_doc_id(doc_id)
        return self.store.add(chunks)
