"""Base ingestion pipeline (Template Method pattern)."""

import logging
from typing import TYPE_CHECKING

from endorag_ingestion.core.base_connector import BaseConnector
from endorag_ingestion.core.base_converter import BaseConverter
from endorag_ingestion.core.base_vector_store import BaseVectorStore
from endorag_ingestion.core.models import (
    Chunk,
    ConvertedDocument,
    DocumentResult,
    ManifestEntry,
    RawDocument,
    RunSummary,
)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:  # the one chunker implementation (no chunker base class)
    from endorag_ingestion.chunker import HybridChunker


class BasePipeline:
    """download -> convert -> chunk -> store, one manifest entry at a time.

    run() owns the sequence and the error handling; the steps are injected strategies.
    A document that fails at any step is recorded and skipped; the run continues.
    Storing upserts by `doc_id`, so re-running never leaves stale or duplicate chunks.
    """

    def __init__(
        self,
        connector: BaseConnector,
        converter: BaseConverter,
        chunker: "HybridChunker",
        storage: BaseVectorStore,
    ) -> None:
        self.connector = connector
        self.converter = converter
        self.chunker = chunker
        self.storage = storage

    def run(self, entries: list[ManifestEntry]) -> RunSummary:
        """Ingest the entries end to end. Disabled entries are skipped."""
        summary = RunSummary()
        for entry in entries:
            if not entry.enabled:
                summary.results.append(DocumentResult(doc_id=entry.id, status="skipped"))
                continue
            try:
                n = self._ingest(entry)
            except Exception as exc:
                logger.exception("Failed to ingest %s", entry.id)
                summary.results.append(
                    DocumentResult(doc_id=entry.id, status="failed", error=repr(exc))
                )
            else:
                logger.info("Ingested %s (%d chunks)", entry.id, n)
                summary.results.append(DocumentResult(doc_id=entry.id, status="ok", chunks=n))
        return summary

    def _ingest(self, entry: ManifestEntry) -> int:
        """Download, convert, chunk and store one entry. Returns the number of chunks."""
        raw = self._download(entry)
        document = self._convert(raw)
        chunks = self._chunk(document)
        if not chunks:
            raise ValueError(f"{entry.id}: conversion produced no chunks")
        return len(self._store(chunks))

    def _download(self, entry: ManifestEntry) -> RawDocument:
        return self.connector.download(entry)

    def _convert(self, raw: RawDocument) -> ConvertedDocument:
        return self.converter.convert(raw)

    def _chunk(self, document: ConvertedDocument) -> list[Chunk]:
        return self.chunker.chunk(document)

    def _store(self, chunks: list[Chunk]) -> list[str]:
        """Replace the document's chunks in the storage (which embeds them)."""
        return self.storage.upsert_documents(chunks)

    def close(self) -> None:
        """Release the connector, the converter and the storage (local Qdrant locks its dir)."""
        self.connector.close()
        self.converter.close()
        self.storage.close()
