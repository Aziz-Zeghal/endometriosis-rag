"""Deterministic safety check: French emergency patterns on normalized text."""

import re
import unicodedata

from endorag_ingestion.core.settings import Profile

from endorag_back.services.safety.base import SafetyCheck, SafetyDecision
from endorag_back.services.safety.patterns import PATTERNS

_NOT_KEPT = re.compile(r"[^a-z0-9°]+")
_REPEATED = re.compile(r"([a-z])\1{2,}")


def normalize(text: str) -> str:
    """Lowercase, remove accents, turn apostrophes and punctuation into single spaces and
    collapse runs of 3+ identical letters ("mourirrr" → "mourir")."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _NOT_KEPT.sub(" ", text)
    return _REPEATED.sub(r"\1", text).strip()


class KeywordSafetyCheck(SafetyCheck):
    """Applies the patterns of `profile` (see `patterns.py`: medical red flags are patient only)."""

    def __init__(self, profile: Profile) -> None:
        self._patterns = [
            (label, kind, re.compile(regex))
            for label, kind, regex, profiles in PATTERNS
            if profile in profiles
        ]

    async def check(self, text: str) -> SafetyDecision:
        normalized = normalize(text)
        hits = [(label, kind) for label, kind, regex in self._patterns if regex.search(normalized)]
        if not hits:
            return SafetyDecision(emergency=False, source="keyword")
        return SafetyDecision(
            emergency=True, kind=hits[0][1], matched=[label for label, _ in hits], source="keyword"
        )
