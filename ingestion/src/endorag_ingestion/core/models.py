"""Pydantic models crossing module boundaries in the ingestion pipeline."""

import uuid
from datetime import date
from pathlib import Path
from typing import Literal, Self

from docling_core.types.doc import DoclingDocument
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Audience = Literal["patient", "gp", "both"]
Format = Literal["html", "pdf", "xml", "video"]  # xml = JATS full text

# Fixed namespace so point ids are stable across runs and machines.
POINT_NAMESPACE = uuid.UUID("6f1c4f7e-2d1a-4b8e-9a43-0e5b1f2c7d10")


class ManifestEntry(BaseModel):
    """One document of a corpus manifest: where to fetch it and how to cite it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    url: HttpUrl  # shown in citations
    fetch_url: HttpUrl | None = None  # downloaded instead of `url` (e.g. an open-access XML API)
    source: str
    title: str
    published: date | None = None
    checked: date | None = None  # "vérifié le", for pages without a publication date
    audience: Audience
    format: Format
    licence: str
    crawl_delay_s: float | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def _has_a_date(self) -> Self:
        if self.published is None and self.checked is None:
            raise ValueError(f"{self.id}: needs a 'published' or 'checked' date")
        return self

    @property
    def citation_date(self) -> date:
        """Date shown with citations and used by the recency rule."""
        return self.published or self.checked  # type: ignore[return-value]


class RawDocument(BaseModel):
    """A fetched document, cached on disk."""

    model_config = ConfigDict(frozen=True)

    entry: ManifestEntry
    path: Path
    content_type: str | None = None
    retrieved: date


class ConvertedDocument(BaseModel):
    """A converted document: docling's structured document, plus a Markdown snapshot."""

    model_config = ConfigDict(frozen=True)

    entry: ManifestEntry
    document: DoclingDocument  # headings, items and (for PDFs) page numbers; what gets chunked
    markdown: str  # human-readable export, for review and debugging
    retrieved: date


class Chunk(BaseModel):
    """A retrievable passage. Its fields are the vector store payload."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    chunk_index: int = Field(ge=0)
    text: str
    heading_path: list[str] = Field(default_factory=list)
    source: str
    title: str
    url: str
    published: date
    retrieved: date
    audience: Audience
    licence: str
    format: Format
    page: int | None = None  # page of the chunk's first item; None for HTML and XML
    start_seconds: float | None = None

    @property
    def point_id(self) -> str:
        """`uuid5(doc_id#chunk_index)`: Qdrant needs UUIDs, and re-ingestion stays idempotent."""
        return str(uuid.uuid5(POINT_NAMESPACE, f"{self.doc_id}#{self.chunk_index}"))

    @property
    def citation_url(self) -> str:
        """`url`, pointing at the chunk's page for PDFs (`#page=N`, read by PDF viewers)."""
        if self.format == "pdf" and self.page is not None:
            return f"{self.url}#page={self.page}"
        return self.url

    @property
    def embedding_text(self) -> str:
        """Text that gets embedded: heading path + content. Metadata stays in the payload."""
        if not self.heading_path:
            return self.text
        return " > ".join(self.heading_path) + "\n\n" + self.text


class ScoredChunk(BaseModel):
    """A chunk returned by a search, with its score."""

    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float  # the store's ranking score (RRF for the hybrid search: rank-based)
    # Cosine similarity of the query and chunk dense vectors: comparable across queries, so
    # it can tell weak evidence apart. None when the store does not compute it.
    dense_score: float | None = None


class DocumentResult(BaseModel):
    doc_id: str
    status: Literal["ok", "failed", "skipped"]
    chunks: int = 0
    error: str | None = None


class RunSummary(BaseModel):
    """Outcome of one pipeline run, one line per manifest entry."""

    results: list[DocumentResult] = Field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(r.status == status for r in self.results)

    @property
    def ok(self) -> int:
        return self.count("ok")

    @property
    def failed(self) -> int:
        return self.count("failed")

    @property
    def skipped(self) -> int:
        return self.count("skipped")
