"""Dispatch on the manifest format, with a Markdown cache in front of the converters."""

import hashlib
import json
import logging
from pathlib import Path

from endorag_ingestion.converters.html import HtmlConverter
from endorag_ingestion.converters.jats import JatsConverter
from endorag_ingestion.converters.pdf import PdfConverter
from endorag_ingestion.core import ConvertedDocument, Converter, RawDocument
from endorag_ingestion.settings import MARKDOWN_DIR

logger = logging.getLogger(__name__)

# Bump when a converter or the cleaning changes its output, so cached Markdown is redone.
CONVERTER_VERSION = 6


class RoutingConverter(Converter):
    """Picks the converter for `entry.format` and caches its output in `MARKDOWN_DIR`.

    `<doc_id>.md` is reused when `<doc_id>.meta.json` records the sha256 of the same raw
    file and the current `CONVERTER_VERSION`, so the index can be rebuilt from the committed
    Markdown without running docling.
    """

    def __init__(
        self,
        converters: dict[str, Converter] | None = None,
        markdown_dir: Path = MARKDOWN_DIR,
    ) -> None:
        self.converters = converters or {
            "html": HtmlConverter(),
            "pdf": PdfConverter(),
            "xml": JatsConverter(),
        }
        self.markdown_dir = markdown_dir

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        doc_id = raw.entry.id
        md_path = self.markdown_dir / f"{doc_id}.md"
        meta_path = self.markdown_dir / f"{doc_id}.meta.json"
        meta = {
            "source_sha256": hashlib.sha256(raw.path.read_bytes()).hexdigest(),
            "converter_version": CONVERTER_VERSION,
        }

        if md_path.exists() and self._cached_meta(meta_path) == meta:
            logger.info("%s: reusing cached Markdown", doc_id)
            markdown = md_path.read_text(encoding="utf-8")
            return ConvertedDocument(entry=raw.entry, markdown=markdown, retrieved=raw.retrieved)

        converter = self.converters.get(raw.entry.format)
        if converter is None:
            raise ValueError(f"{doc_id}: no converter for format {raw.entry.format!r}")
        doc = converter.convert(raw)

        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(doc.markdown, encoding="utf-8")
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return doc

    @staticmethod
    def _cached_meta(meta_path: Path) -> dict | None:
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))
