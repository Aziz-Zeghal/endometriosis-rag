"""JATS XML (open-access journal full text) to a DoclingDocument with docling. No models."""

from docling_core.types.doc import DoclingDocument

from endorag_ingestion.core import BaseConverter, RawDocument


class JatsConverter(BaseConverter):
    def __init__(self) -> None:
        self._docling = None

    def _converter(self):
        if self._docling is None:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter

            self._docling = DocumentConverter(allowed_formats=[InputFormat.XML_JATS])
        return self._docling

    def _parse(self, raw: RawDocument) -> DoclingDocument:
        return self._converter().convert(raw.path).document
