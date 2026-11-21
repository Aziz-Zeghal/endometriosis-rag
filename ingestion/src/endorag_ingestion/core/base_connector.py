"""Base class for data source connectors (Template Method pattern)."""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from endorag_ingestion.core.models import ManifestEntry, RawDocument
from endorag_ingestion.core.settings import RAW_DIR


class BaseConnector(ABC):
    """Downloads manifest entries into an offline-first disk cache.

    download() owns the cache: `<raw_dir>/<doc_id>.<format>` plus `<doc_id>.meta.json`.
    A cached entry is returned without calling the source; `refresh=True` downloads again.
    Subclasses only implement _download_to(), the source-specific download.
    """

    def __init__(self, raw_dir: Path = RAW_DIR, refresh: bool = False) -> None:
        self.raw_dir = raw_dir
        self.refresh = refresh

    @abstractmethod
    def _download_to(self, entry: ManifestEntry, path: Path) -> dict:
        """Write the entry's content to `path`; return what the meta file should record
        about the source (URL, status, `content_type`...). Raise if it cannot be downloaded,
        leaving `path` unwritten."""

    def download(self, entry: ManifestEntry) -> RawDocument:
        """The entry's raw file, from the cache or freshly downloaded."""
        path = self.raw_dir / f"{entry.id}.{entry.format}"
        meta_path = self.raw_dir / f"{entry.id}.meta.json"
        if not self.refresh and path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            meta = self._download_to(entry, path) | {
                "retrieved": date.today().isoformat(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            # Written last: a complete meta file marks a complete cache entry.
            meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return RawDocument(
            entry=entry,
            path=path,
            content_type=meta.get("content_type"),
            retrieved=date.fromisoformat(meta["retrieved"]),
        )

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the connector. Default: nothing to release."""
