"""PDF to Markdown with docling (layout model, table structure, no OCR)."""

from endorag_ingestion.converters.cleaning import clean_markdown, strip_page_numbers
from endorag_ingestion.core import ConvertedDocument, Converter, RawDocument


class PdfConverter(Converter):
    """The docling converter loads models, so it is built on first use and then reused.

    OCR is off: the corpus PDFs have a text layer, and OCR is the slowest step.
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
        result = self._converter().convert(raw.path)
        markdown = result.document.export_to_markdown(image_placeholder="")
        markdown = clean_markdown(strip_page_numbers(markdown))
        if not markdown.strip():
            raise ValueError(f"{raw.entry.id}: docling extracted no content")
        return ConvertedDocument(entry=raw.entry, markdown=markdown, retrieved=raw.retrieved)
