"""Composition root: the one place that decides which strategy implements each step."""

from endorag_ingestion.chunkers import MarkdownChunker
from endorag_ingestion.connectors import HttpConnector
from endorag_ingestion.converters import RoutingConverter
from endorag_ingestion.embedders import make_embedder
from endorag_ingestion.pipeline import Pipeline
from endorag_ingestion.settings import Settings
from endorag_ingestion.stores import QdrantStore


def build_pipeline(settings: Settings, refresh: bool = False) -> Pipeline:
    """Wire the default strategies from `settings`. `refresh` re-fetches cached raw files.

    Nothing heavy happens here: the HTTP client, docling and BM25 models load on first use.
    The caller closes `pipeline.store` (local Qdrant locks its directory).
    """
    embedder = make_embedder(settings)
    store = QdrantStore(
        collection=settings.collection_name(),
        dimension=embedder.dimension,
        path=settings.qdrant_path,
    )
    return Pipeline(
        connector=HttpConnector(settings, refresh=refresh),
        converter=RoutingConverter(),
        chunker=MarkdownChunker(
            settings.chunk_size, settings.chunk_overlap, settings.chunk_min_chars
        ),
        embedder=embedder,
        store=store,
    )
