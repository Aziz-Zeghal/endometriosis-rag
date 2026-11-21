"""Embeddings through an OpenAI-compatible endpoint: batched, retried, cached on disk."""

import hashlib
import logging
import re
import sqlite3
import threading
import time
from array import array
from pathlib import Path

import openai
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from endorag_ingestion.core.settings import CACHE_DIR

log = logging.getLogger(__name__)

# Dimensions measured on the endpoint; other models are probed once.
KNOWN_DIMENSIONS = {"nemotron-3-embed-1b": 2048, "gemini-embedding-001": 3072}

# A batch of 128 hits the gateway's 30 s upstream limit; 16 takes about 1.2 s.
BATCH_SIZE = 16
MAX_ATTEMPTS = 6
BACKOFF_START_S = 2.0
BACKOFF_CAP_S = 60.0


def _is_transient(exc: Exception) -> bool:
    """Connection errors, timeouts (APITimeoutError is an APIConnectionError), 429 and 5xx."""
    if isinstance(exc, openai.APIConnectionError | openai.RateLimitError):
        return True
    return isinstance(exc, openai.APIStatusError) and exc.status_code >= 500


class EmbeddingCache:
    """sqlite map sha256(text) -> float32 vector. One file per model.

    Thread-safe: the backend builds the embedder once and calls it from worker threads.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vec BLOB)")

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_many(self, texts: list[str]) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        with self._lock:
            for text in set(texts):
                row = self._db.execute(
                    "SELECT vec FROM embeddings WHERE key = ?", (self.key(text),)
                ).fetchone()
                if row is not None:
                    found[text] = array("f", row[0]).tolist()
        return found

    def put_many(self, texts: list[str], vectors: list[list[float]]) -> None:
        rows = [(self.key(t), array("f", v).tobytes()) for t, v in zip(texts, vectors, strict=True)]
        with self._lock, self._db:  # commits, so a crash after this batch keeps it
            self._db.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?)", rows)


def default_cache_path(model: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
    return CACHE_DIR / "embeddings" / f"{safe}.sqlite"


class OpenAICompatibleEmbedder(Embeddings):
    """`OpenAIEmbeddings` against the LLM endpoint, protected against disconnections.

    A LangChain `Embeddings`, plus `name` and `dimension` (the vector store sizes its
    collection with it).
    """

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        cache_path: Path | None = None,
        batch_size: int = BATCH_SIZE,
        client: OpenAIEmbeddings | None = None,
    ) -> None:
        self.name = model
        self.batch_size = batch_size
        self._client = client or OpenAIEmbeddings(
            model=model,
            base_url=base_url,
            api_key=api_key,
            check_embedding_ctx_length=False,  # no tiktoken split for non-OpenAI models
            max_retries=0,  # retries are handled per batch below
            request_timeout=60,
        )
        self._cache = EmbeddingCache(cache_path or default_cache_path(model))
        self._dimension = KNOWN_DIMENSIONS.get(model)

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = len(self.embed_query("dimension"))
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        found = self._cache.get_many(texts)
        missing = list(dict.fromkeys(t for t in texts if t not in found))
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start : start + self.batch_size]
            vectors = self._embed_with_retry(batch)
            self._cache.put_many(batch, vectors)
            found.update(zip(batch, vectors, strict=True))
        return [found[t] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        # The endpoint embeds queries and documents the same way, so they share the cache.
        return self.embed_documents([text])[0]

    def _embed_with_retry(self, batch: list[str]) -> list[list[float]]:
        delay = BACKOFF_START_S
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._client.embed_documents(batch)
            except Exception as exc:
                if attempt == MAX_ATTEMPTS or not _is_transient(exc):
                    raise
                log.warning("embedding batch failed (%s), retry %d in %.0f s", exc, attempt, delay)
                time.sleep(delay)
                delay = min(delay * 2, BACKOFF_CAP_S)
        raise AssertionError("unreachable")
