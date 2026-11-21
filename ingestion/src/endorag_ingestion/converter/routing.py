"""Dispatch on the manifest format."""

from docling_core.types.doc import DoclingDocument

from endorag_ingestion.converter.cleaning import CleaningConverter
from endorag_ingestion.converter.html import HtmlConverter
from endorag_ingestion.converter.jats import JatsConverter
from endorag_ingestion.converter.pdf import PdfConverter
from endorag_ingestion.core import BaseConverter, RawDocument


class RoutingConverter(CleaningConverter):
    """Picks the converter for `entry.format`; it only routes (the cache is `CachedConverter`).

    `BaseConverter.convert()` runs its template through the router. `_parse` and `_repair`
    receive the raw document, so they route to the format's converter. `_enrich` receives
    only the DoclingDocument and could not route, so `_parse` runs the routed converter's
    `_enrich` (cleaning, plus e.g. the HTML trailer removal) and the router's own `_enrich`
    does nothing. `_markdown` is the shared clean snapshot of `CleaningConverter`.
    """

    def __init__(self, converters: dict[str, BaseConverter] | None = None) -> None:
        self.converters = converters or {
            "html": HtmlConverter(),
            "pdf": PdfConverter(),
            "xml": JatsConverter(),
        }

    def _route(self, raw: RawDocument) -> BaseConverter:
        converter = self.converters.get(raw.entry.format)
        if converter is None:
            raise ValueError(f"{raw.entry.id}: no converter for format {raw.entry.format!r}")
        return converter

    def _parse(self, raw: RawDocument) -> DoclingDocument:
        converter = self._route(raw)
        document = converter._parse(raw)
        converter._enrich(document)
        return document

    def _repair(self, raw: RawDocument, error: Exception) -> RawDocument:
        return self._route(raw)._repair(raw, error)

    def _enrich(self, document: DoclingDocument) -> None:
        """Nothing: the routed converter's `_enrich` already ran in `_parse`."""

    def close(self) -> None:
        """Close each distinct routed converter once."""
        for converter in set(self.converters.values()):
            converter.close()
