"""Paths and configuration. Nothing else in the package hard-codes a path."""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # fetched HTML/PDF snapshot (committed)
MARKDOWN_DIR = DATA_DIR / "markdown"  # converted documents (committed)
QDRANT_DIR = DATA_DIR / "qdrant"  # local vector database (gitignored, rebuilt)
MANIFESTS_DIR = ROOT_DIR / "ingestion" / "manifests"

Profile = Literal["patient", "gp"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    profile: Profile = "patient"
    embedder: str = "nemotron-3-embed-1b"
    qdrant_path: Path = QDRANT_DIR
    user_agent: str = "endorag-research-bot/0.1 (non-commercial research demo)"

    # Only needed by the OpenAI-compatible embedder; the backend makes them required.
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("LLM_API_KEY", "FREELLMAPI_API_KEY")
    )

    def collection_name(self) -> str:
        """`<profile>__<embedder>`, so changing models never mixes vector spaces."""
        return f"{self.profile}__{self.embedder.replace('/', '_')}"
