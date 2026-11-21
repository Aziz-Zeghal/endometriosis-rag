"""Paths and configuration. Nothing else in the package hard-codes a path."""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # fetched HTML/PDF snapshot (committed)
MARKDOWN_DIR = DATA_DIR / "markdown"  # converted documents: .md + .docling.json (committed)
QDRANT_DIR = DATA_DIR / "qdrant"  # local vector database (gitignored, rebuilt)
CACHE_DIR = DATA_DIR / "cache"  # embedding cache (gitignored)
MANIFESTS_DIR = ROOT_DIR / "ingestion" / "manifests"

Profile = Literal["patient", "gp"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    profile: Profile = "patient"
    embedder: str = "nemotron-3-embed-1b"
    qdrant_path: Path = QDRANT_DIR
    # Chunks are sized with the embedder's own tokenizer (Hugging Face id of its weights).
    chunk_tokenizer: str = "nvidia/Nemotron-3-Embed-1B-BF16"
    chunk_max_tokens: int = 512
    chunk_min_chars: int = 40  # chunks with fewer letters and digits are dropped
    user_agent: str = "endorag-research-bot/0.1 (non-commercial research demo)"

    # The embedding endpoint (needed by build_storage); the backend makes them required.
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("LLM_API_KEY", "FREELLMAPI_API_KEY")
    )

    def collection_name(self) -> str:
        """`<profile>__<embedder>`, so changing models never mixes vector spaces."""
        return f"{self.profile}__{self.embedder.replace('/', '_')}"
