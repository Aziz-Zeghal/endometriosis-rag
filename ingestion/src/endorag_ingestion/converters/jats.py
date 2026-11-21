"""JATS XML (open-access journal full text) to Markdown with docling. No models are loaded."""

from endorag_ingestion.converters.cleaning import clean_markdown
from endorag_ingestion.core import ConvertedDocument, Converter, RawDocument


class JatsConverter(Converter):
    def __init__(self) -> None:
        self._docling = None

    def _converter(self):
        if self._docling is None:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter

            self._docling = DocumentConverter(allowed_formats=[InputFormat.XML_JATS])
        return self._docling

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        result = self._converter().convert(raw.path)
        markdown = clean_markdown(result.document.export_to_markdown(image_placeholder=""))
        if not markdown.strip():
            raise ValueError(f"{raw.entry.id}: docling extracted no content from the XML")
        return ConvertedDocument(entry=raw.entry, markdown=markdown, retrieved=raw.retrieved)
