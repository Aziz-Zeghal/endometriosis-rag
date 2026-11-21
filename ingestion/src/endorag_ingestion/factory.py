"""Composition root: the one place that decides which strategy implements each step."""

from endorag_ingestion.chunker import HybridTextChunker
from endorag_ingestion.connector import HttpConnector
from endorag_ingestion.converter import RoutingConverter
from endorag_ingestion.core import BasePipeline, Settings
from endorag_ingestion.embedder import make_embedder
from endorag_ingestion.vector_storage import QdrantStore


def build_pipeline(settings: Settings, refresh: bool = False) -> BasePipeline:
    """Wire the default strategies from `settings`. `refresh` re-downloads cached raw files.

    Nothing heavy happens here: the HTTP client, docling, the tokenizer and BM25 models load
    on first use.
    The caller calls `pipeline.close()` (local Qdrant locks its directory).
    """
    storage = QdrantStore(
        collection=settings.collection_name(),
        embedding=make_embedder(settings),
        path=settings.qdrant_path,
    )
    return BasePipeline(
        connector=HttpConnector(settings, refresh=refresh),
        converter=RoutingConverter(),
        chunker=HybridTextChunker(
            settings.chunk_tokenizer, settings.chunk_max_tokens, settings.chunk_min_chars
        ),
        storage=storage,
    )
