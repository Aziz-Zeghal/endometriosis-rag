"""Embedding providers (LangChain `Embeddings`) and the factory that picks one from
`Settings.embedder`.

Not a pipeline step: the embedding is injected into the vector store, which owns it.
"""

from langchain_core.embeddings import Embeddings

from endorag_ingestion.core import Settings
from endorag_ingestion.embedder import openai_compatible, sentence_transformers
from endorag_ingestion.embedder.openai_compatible import OpenAICompatibleEmbedder
from endorag_ingestion.embedder.sentence_transformers import PRESETS, SentenceTransformerEmbedder


def make_embedder(settings: Settings) -> Embeddings:
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


__all__ = [
    "OpenAICompatibleEmbedder",
    "SentenceTransformerEmbedder",
    "make_embedder",
    "openai_compatible",
    "sentence_transformers",
]
