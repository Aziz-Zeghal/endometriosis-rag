"""In-memory fakes for every pipeline interface (offline tests)."""

from datetime import date
from pathlib import Path

from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.types.doc import DocItemLabel, DoclingDocument
from endorag_ingestion.core import (
    BaseChunker,
    BaseConnector,
    BaseConverter,
    BaseVectorStore,
    Chunk,
    ConvertedDocument,
    ManifestEntry,
    RawDocument,
    ScoredChunk,
)
from langchain_core.embeddings import Embeddings

TODAY = date(2026, 11, 21)


def make_entry(doc_id: str = "doc-a", **kw) -> ManifestEntry:
    data = dict(
        id=doc_id,
        url=f"https://example.org/{doc_id}",
        source="Example",
        title=f"Title {doc_id}",
        published=date(2026, 1, 1),
        audience="patient",
        format="html",
        licence="all-rights-reserved",
    )
    data.update(kw)
    return ManifestEntry(**data)


class FakeConnector(BaseConnector):
    """Downloads into `raw_dir` (a test's tmp_path): a few bytes per entry, no network."""

    def __init__(self, raw_dir: Path, failing: set[str] | None = None) -> None:
        super().__init__(raw_dir=raw_dir)
        self.failing = failing or set()

    def _download_to(self, entry: ManifestEntry, path: Path) -> dict:
        if entry.id in self.failing:
            raise ConnectionError(f"cannot fetch {entry.id}")
        path.write_bytes(entry.id.encode())
        return {"content_type": "text/plain"}


class FakeConverter(BaseConverter):
    """A title and `paragraphs` paragraphs; BaseConverter adds the Markdown snapshot."""

    def __init__(self, paragraphs: int = 2) -> None:
        self.paragraphs = paragraphs

    def _parse(self, raw: RawDocument) -> DoclingDocument:
        document = DoclingDocument(name=raw.entry.id)
        document.add_title(raw.entry.title)
        for i in range(self.paragraphs):
            document.add_text(label=DocItemLabel.TEXT, text=f"Paragraph {i} of {raw.entry.id}.")
        return document


class FakeChunker(BaseChunker):
    def chunk(self, document: ConvertedDocument) -> list[Chunk]:
        e = document.entry
        parts = [p for p in document.markdown.split("\n\n")[1:] if p.strip()]
        return [
            Chunk(
                doc_id=e.id,
                chunk_index=i,
                text=p,
                heading_path=[e.title],
                source=e.source,
                title=e.title,
                url=str(e.url),
                published=e.citation_date,
                retrieved=document.retrieved,
                audience=e.audience,
                licence=e.licence,
                format=e.format,
            )
            for i, p in enumerate(parts)
        ]


class WordTokenizer(BaseTokenizer):
    """Offline stand-in for a Hugging Face tokenizer: one token per word."""

    max_tokens: int = 64

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def get_max_tokens(self) -> int:
        return self.max_tokens

    def get_tokenizer(self):
        return self.count_tokens  # semchunk accepts a token-counting function


class FakeEmbedder(Embeddings):
    name = "fake"

    @property
    def dimension(self) -> int:
        return 3

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), float(text.count(" ")), 1.0]


class InMemoryStore(BaseVectorStore):
    def __init__(self, embedding: Embeddings | None = None) -> None:
        self.embedding = embedding or FakeEmbedder()
        self.points: dict[str, tuple[Chunk, list[float]]] = {}

    def add_documents(self, chunks: list[Chunk]) -> list[str]:
        vectors = self.embedding.embed_documents([c.embedding_text for c in chunks])
        for c, v in zip(chunks, vectors, strict=True):
            self.points[c.point_id] = (c, v)
        return [c.point_id for c in chunks]

    def delete_by_metadata(self, field: str, value: str) -> int:
        kept = {k: p for k, p in self.points.items() if getattr(p[0], field) != value}
        deleted = len(self.points) - len(kept)
        self.points = kept
        return deleted

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        hits = [ScoredChunk(chunk=c, score=1.0) for c, _ in self.points.values()]
        return hits[:k]
