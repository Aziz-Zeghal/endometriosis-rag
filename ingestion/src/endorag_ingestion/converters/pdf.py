"""PDF to a DoclingDocument with docling (layout model, table structure, no OCR)."""

from endorag_ingestion.converters.cleaning import to_converted
from endorag_ingestion.core import ConvertedDocument, Converter, RawDocument


class PdfConverter(Converter):
    """The docling converter loads models, so it is built on first use and then reused.

    OCR is off: the corpus PDFs have a text layer, and OCR is the slowest step. The
    DoclingDocument keeps each item's page number, used for page-level citations.
    """

    def __init__(self) -> None:
        self._docling = None

    def _converter(self):
        if self._docling is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
            self._docling = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
            )
        return self._docling

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        return to_converted(raw, self._converter().convert(raw.path).document)
