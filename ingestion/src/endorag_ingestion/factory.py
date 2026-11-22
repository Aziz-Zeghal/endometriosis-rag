"""Composition root: the one place that decides which strategy implements each step."""

from qdrant_client import QdrantClient

from endorag_ingestion.chunker import HybridChunker
from endorag_ingestion.connector import HttpConnector
from endorag_ingestion.converter.cleaning import clean_text
from endorag_ingestion.core import BasePipeline, Settings
from endorag_ingestion.embedder import OpenAICompatibleEmbedder
from endorag_ingestion.vector_storage import QdrantStore


def build_storage(settings: Settings, client: QdrantClient | None = None) -> QdrantStore:
    """The vector store and its embedder only: what `query`, `stats` and the backend need.

    Needs no conversion dependencies. Without `client`, the store opens its own client on
    `settings.qdrant_path` and the caller calls `close()` (local Qdrant locks its directory).
    With `client` (one shared by several collections, as the backend does for both
    profiles), the caller closes that client instead.
    """
    if not settings.llm_base_url or not settings.llm_api_key:
        raise ValueError(
            f"Embedder {settings.embedder!r} calls the API: set LLM_BASE_URL and LLM_API_KEY."
        )
    embedding = OpenAICompatibleEmbedder(
        settings.embedder, settings.llm_base_url, settings.llm_api_key.get_secret_value()
    )
    return QdrantStore(
        collection=settings.collection_name(),
        embedding=embedding,
        path=None if client else settings.qdrant_path,
        client=client,
    )


def build_pipeline(settings: Settings, refresh: bool = False) -> BasePipeline:
    """Wire the default strategies from `settings`. `refresh` re-downloads cached raw files.

    Nothing heavy happens here: the HTTP client, docling, the tokenizer and BM25 models load
    on first use. The converters need the `[ingest]` extra.
    The caller calls `pipeline.close()` (local Qdrant locks its directory).
    """
    try:
        import docling  # noqa: F401

        from endorag_ingestion.converter.cached import CachedConverter
        from endorag_ingestion.converter.routing import RoutingConverter
    except ImportError as exc:
        raise ImportError(
            f"Ingestion needs the conversion dependencies ({exc.name} is missing): "
            'install endorag-ingestion[ingest], e.g. uv pip install -e "./ingestion[ingest]".'
        ) from exc
    return BasePipeline(
        connector=HttpConnector(settings, refresh=refresh),
        converter=CachedConverter(RoutingConverter()),
        chunker=HybridChunker(
            settings.chunk_tokenizer,
            settings.chunk_max_tokens,
            settings.chunk_min_chars,
            text_cleaner=clean_text,
        ),
        storage=build_storage(settings),
    )
