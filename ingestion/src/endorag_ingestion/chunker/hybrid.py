"""Text chunker for HTML, PDF and JATS documents."""

from endorag_ingestion.core import BaseHybridChunker


class HybridTextChunker(BaseHybridChunker):
    """Text chunks only: the default of `BaseHybridChunker`.

    A modality with its own chunks (e.g. video transcripts with time offsets) would be a
    sibling subclass overriding `chunk()` on top of `_text_chunks()`.
    """
