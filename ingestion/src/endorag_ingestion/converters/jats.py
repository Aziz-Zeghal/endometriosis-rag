"""JATS XML (open-access journal full text) to a DoclingDocument with docling. No models."""

from endorag_ingestion.converters.cleaning import to_converted
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
        return to_converted(raw, self._converter().convert(raw.path).document)
