"""Embedder strategies and the factory that picks one from `Settings.embedder`."""

from endorag_ingestion.core import Embedder
from endorag_ingestion.embedders.openai_compatible import OpenAICompatibleEmbedder
from endorag_ingestion.embedders.sentence_transformers import PRESETS, SentenceTransformerEmbedder
from endorag_ingestion.settings import Settings


def make_embedder(settings: Settings) -> Embedder:
    """Local presets (`org/model`) run locally; plain ids go to the API endpoint."""
    if settings.embedder in PRESETS:
        return SentenceTransformerEmbedder.from_preset(settings.embedder)
    if "/" in settings.embedder:
        # Local models load with trust_remote_code, so only reviewed presets are allowed.
        raise ValueError(
            f"Unknown local embedder {settings.embedder!r}; choose one of {sorted(PRESETS)}."
        )
    if not settings.llm_base_url or not settings.llm_api_key:
        raise ValueError(
            f"Embedder {settings.embedder!r} calls the API: set LLM_BASE_URL and LLM_API_KEY."
        )
    api_key = settings.llm_api_key.get_secret_value()
    return OpenAICompatibleEmbedder(settings.embedder, settings.llm_base_url, api_key)


__all__ = ["OpenAICompatibleEmbedder", "SentenceTransformerEmbedder", "make_embedder"]
