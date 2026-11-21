"""The embedder: a LangChain `Embeddings` over the OpenAI-compatible endpoint.

Not a pipeline step: the embedding is injected into the vector store, which owns it.
"""

from endorag_ingestion.embedder import openai_compatible
from endorag_ingestion.embedder.openai_compatible import OpenAICompatibleEmbedder

__all__ = ["OpenAICompatibleEmbedder", "openai_compatible"]
