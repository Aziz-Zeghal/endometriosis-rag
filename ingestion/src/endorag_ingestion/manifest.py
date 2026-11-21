"""Load and validate the corpus manifests (`ingestion/manifests/<profile>.yaml`)."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from endorag_ingestion.core import ManifestEntry
from endorag_ingestion.settings import MANIFESTS_DIR


def load_manifest(profile: str, manifests_dir: Path = MANIFESTS_DIR) -> list[ManifestEntry]:
    """Every entry of a manifest, validated, enabled or not. Duplicate ids are an error."""
    path = manifests_dir / f"{profile}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of entries")

    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for i, item in enumerate(data):
        try:
            entry = ManifestEntry.model_validate(item)
        except ValidationError as exc:
            raise ValueError(f"{path}: invalid entry #{i}: {exc}") from exc
        if entry.id in seen:
            raise ValueError(f"{path}: duplicate id '{entry.id}'")
        seen.add(entry.id)
        entries.append(entry)
    return entries


def load_entries(
    profile: str, only: list[str] | None = None, manifests_dir: Path = MANIFESTS_DIR
) -> list[ManifestEntry]:
    """Entries to ingest: the enabled ones, or exactly the ids in `only` (even if disabled)."""
    entries = load_manifest(profile, manifests_dir)
    if only is None:
        return [e for e in entries if e.enabled]
    unknown = set(only) - {e.id for e in entries}
    if unknown:
        raise ValueError(f"unknown ids in the {profile} manifest: {sorted(unknown)}")
    # An explicit selection overrides `enabled: false`.
    return [e.model_copy(update={"enabled": True}) for e in entries if e.id in only]
