"""Document cache in front of any converter (Decorator pattern)."""

import hashlib
import json
import logging
from pathlib import Path

from docling_core.types.doc import DoclingDocument

from endorag_ingestion.core import BaseConverter, ConvertedDocument, RawDocument
from endorag_ingestion.core.settings import MARKDOWN_DIR

logger = logging.getLogger(__name__)

# Bump when a converter or the cleaning changes its output, so the cache is redone.
CONVERTER_VERSION = 10


class CachedConverter(BaseConverter):
    """Wraps a converter and caches its output in `MARKDOWN_DIR`.

    The cache holds `<doc_id>.docling.json` (the DoclingDocument, which the chunker reads)
    and `<doc_id>.md` (a readable snapshot). Both are reused when `<doc_id>.meta.json`
    records the sha256 of the same raw file and the current `CONVERTER_VERSION`, so the
    index can be rebuilt from the committed files without running trafilatura or docling.
    The wrapped converter runs its full lifecycle only on a cache miss.
    """

    def __init__(self, converter: BaseConverter, markdown_dir: Path = MARKDOWN_DIR) -> None:
        self.converter = converter
        self.markdown_dir = markdown_dir

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        doc_id = raw.entry.id
        md_path = self.markdown_dir / f"{doc_id}.md"
        json_path = self.markdown_dir / f"{doc_id}.docling.json"
        meta_path = self.markdown_dir / f"{doc_id}.meta.json"
        meta = {
            "source_sha256": hashlib.sha256(raw.path.read_bytes()).hexdigest(),
            "converter_version": CONVERTER_VERSION,
        }

        if md_path.exists() and json_path.exists() and self._cached_meta(meta_path) == meta:
            logger.info("%s: reusing cached conversion", doc_id)
            return ConvertedDocument(
                entry=raw.entry,
                document=DoclingDocument.load_from_json(json_path),
                markdown=md_path.read_text(encoding="utf-8"),
                retrieved=raw.retrieved,
            )

        doc = self.converter.convert(raw)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(doc.markdown, encoding="utf-8")
        doc.document.save_as_json(json_path)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return doc

    def _parse(self, raw: RawDocument) -> DoclingDocument:
        # Never called: the decorator wraps convert() whole.
        raise NotImplementedError("CachedConverter wraps convert()")

    def close(self) -> None:
        self.converter.close()

    @staticmethod
    def _cached_meta(meta_path: Path) -> dict | None:
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))
