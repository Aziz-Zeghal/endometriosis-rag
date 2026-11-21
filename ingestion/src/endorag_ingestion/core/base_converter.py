"""Base class for document converters (Template Method pattern)."""

from abc import ABC, abstractmethod

from docling_core.types.doc import DoclingDocument

from endorag_ingestion.core.cleaning import clean_document, clean_text
from endorag_ingestion.core.models import ConvertedDocument, RawDocument


class BaseConverter(ABC):
    """Turns a raw file into a `ConvertedDocument`.

    convert() orchestrates the conversion lifecycle:

    1. _parse   — turn the raw file into a DoclingDocument (required, format-specific).
    2. _repair  — recover an unparseable file and return a raw document to parse once more
                  (optional; default: no repair, re-raise).
    3. _enrich  — clean the DoclingDocument in place before chunking (default: remove
                  tables of contents, the back matter and blank annex forms).

    It then adds the Markdown snapshot (for review) and the entry's metadata.
    """

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        """Parse a raw file (repairing once on failure), enrich it, add its Markdown."""
        try:
            document = self._parse(raw)
        except Exception as exc:
            document = self._parse(self._repair(raw, exc))
        self._enrich(document)
        markdown = clean_text(document.export_to_markdown(image_placeholder=""))
        if not markdown:
            raise ValueError(f"{raw.entry.id}: no content extracted")
        return ConvertedDocument(
            entry=raw.entry, document=document, markdown=markdown + "\n", retrieved=raw.retrieved
        )

    @abstractmethod
    def _parse(self, raw: RawDocument) -> DoclingDocument:
        """Convert a raw file into a DoclingDocument."""

    def _repair(self, raw: RawDocument, error: Exception) -> RawDocument:
        """Recover an unparseable file, returning a raw document to parse once more.

        Default: no repair available, re-raise the original error.
        """
        raise error

    def _enrich(self, document: DoclingDocument) -> None:
        """Clean the parsed document in place before chunking."""
        clean_document(document)

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the converter. Default: nothing to release."""
