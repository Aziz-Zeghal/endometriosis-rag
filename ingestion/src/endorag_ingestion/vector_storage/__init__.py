"""Vector store implementations.

Each backend receives an `Embeddings` at init and owns the embed-and-store operation.
"""

from . import qdrant
from .qdrant import QdrantStore

__all__ = ["QdrantStore", "qdrant"]
