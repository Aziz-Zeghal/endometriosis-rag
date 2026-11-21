"""Composition root: the one place that decides which strategy implements each step."""

from endorag_ingestion.connector import HttpConnector
from endorag_ingestion.converter.cleaning import clean_text
from endorag_ingestion.core import BaseHybridChunker, BasePipeline, Settings
from endorag_ingestion.embedder import make_embedder
from endorag_ingestion.vector_storage import QdrantStore


def build_storage(settings: Settings) -> QdrantStore:
    """The vector store and its embedder only: what `query`, `stats` and the backend need.

    Needs no conversion dependencies. The caller calls `close()` (local Qdrant locks its
    directory).
    """
    return QdrantStore(
        collection=settings.collection_name(),
        embedding=make_embedder(settings),
        path=settings.qdrant_path,
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
        chunker=BaseHybridChunker(
            settings.chunk_tokenizer,
            settings.chunk_max_tokens,
            settings.chunk_min_chars,
            text_cleaner=clean_text,
        ),
        storage=build_storage(settings),
    )
