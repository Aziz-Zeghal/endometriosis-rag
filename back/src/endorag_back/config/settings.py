"""Backend settings: the ingestion settings (same `.env`) plus the chat models and the graph.

The parameters of the graph nodes are all declared here, so nodes read them from one place.
"""

from endorag_ingestion.core.settings import Settings as IngestionSettings
from pydantic import AliasChoices, Field, SecretStr


class Settings(IngestionSettings):
    # The OpenAI-compatible endpoint: optional for ingestion, required here.
    # min_length=1: an empty value copied from .env.example fails at startup, not at first call.
    llm_base_url: str = Field(min_length=1)
    llm_api_key: SecretStr = Field(
        min_length=1, validation_alias=AliasChoices("LLM_API_KEY", "FREELLMAPI_API_KEY")
    )
    llm_model: str = Field(min_length=1)  # generate, clarify
    llm_small_model: str = Field(min_length=1)  # safety check, router, rewrite, triage
    llm_timeout_s: float = 60.0
    # Sent as `reasoning_effort` to both models when set ("none" turns Nemotron 3 reasoning
    # off: the classification calls drop from ~2.5 s to ~0.8 s, docs/method.md D-25).
    llm_reasoning_effort: str | None = None

    # Widget hosts allowed to call the API (Vite dev and preview servers by default).
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:4173"]
    )
    history_messages: int = 6  # past messages (user and assistant) given to the graph

    # Safety gate: the keyword check always runs; the LLM check can be turned off.
    safety_llm_enabled: bool = True
    safety_timeout_s: float = 10.0  # on timeout the keyword result stands

    # Retrieval: hybrid candidates, then dedup, per-document cap, rerank and top_k; the
    # evidence verdict compares the best dense score with min_dense_score.
    retrieve_candidates: int = 20
    retrieve_top_k: int = 5
    max_chunks_per_doc: int = 2
    min_dense_score: float = 0.45  # dense cosine, calibrated on both indexes (docs/method.md)
    dedup_similarity: float = 0.95  # chunks more similar than this are near-duplicates

    # Generation
    temperature: float = 0.2
    max_tokens: int = 1024
