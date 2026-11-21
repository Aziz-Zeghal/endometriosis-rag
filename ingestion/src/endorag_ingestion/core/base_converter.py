"""Base class for document converters (Template Method pattern)."""

from abc import ABC, abstractmethod

from docling_core.types.doc import DoclingDocument

from endorag_ingestion.core.models import ConvertedDocument, RawDocument


class BaseConverter(ABC):
    """Turns a raw file into a `ConvertedDocument`.

    convert() orchestrates the conversion lifecycle:

    1. _parse   — turn the raw file into a DoclingDocument (required, format-specific).
    2. _repair  — recover an unparseable file and return a raw document to parse once more
                  (optional; default: no repair, re-raise).
    3. _enrich  — preprocess the DoclingDocument in place before chunking
                  (optional; default: no-op).

    It then adds the Markdown snapshot (`_markdown`, for review) and the entry's metadata.
    """

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        """Parse a raw file (repairing once on failure), enrich it, add its Markdown."""
        try:
            document = self._parse(raw)
        except Exception as exc:
            document = self._parse(self._repair(raw, exc))
        self._enrich(document)
        markdown = self._markdown(document)
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

    def _enrich(self, document: DoclingDocument) -> None:  # noqa: B027
        """Preprocess the parsed document in place before chunking. Default: nothing."""

    def _markdown(self, document: DoclingDocument) -> str:
        """The Markdown snapshot of the document. Default: docling's export."""
        return document.export_to_markdown(image_placeholder="").strip()

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the converter. Default: nothing to release."""
