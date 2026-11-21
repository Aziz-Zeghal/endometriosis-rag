"""In-memory fakes for every pipeline interface (offline tests)."""

from datetime import date
from pathlib import Path

from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.types.doc import DocItemLabel, DoclingDocument
from endorag_ingestion.core import (
    Chunk,
    Chunker,
    Connector,
    ConvertedDocument,
    Converter,
    Embedder,
    ManifestEntry,
    RawDocument,
    ScoredChunk,
    VectorStore,
)

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


class FakeConnector(Connector):
    def __init__(self, failing: set[str] | None = None) -> None:
        self.failing = failing or set()

    def fetch(self, entry: ManifestEntry) -> RawDocument:
        if entry.id in self.failing:
            raise ConnectionError(f"cannot fetch {entry.id}")
        return RawDocument(entry=entry, path=Path(f"/fake/{entry.id}"), retrieved=TODAY)


class FakeConverter(Converter):
    def __init__(self, paragraphs: int = 2) -> None:
        self.paragraphs = paragraphs

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        paragraphs = [f"Paragraph {i} of {raw.entry.id}." for i in range(self.paragraphs)]
        document = DoclingDocument(name=raw.entry.id)
        document.add_title(raw.entry.title)
        for p in paragraphs:
            document.add_text(label=DocItemLabel.TEXT, text=p)
        return ConvertedDocument(
            entry=raw.entry,
            document=document,
            markdown=f"# {raw.entry.title}\n\n" + "\n\n".join(paragraphs),
            retrieved=raw.retrieved,
        )


class FakeChunker(Chunker):
    def chunk(self, doc: ConvertedDocument) -> list[Chunk]:
        e = doc.entry
        parts = [p for p in doc.markdown.split("\n\n")[1:] if p.strip()]
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
                retrieved=doc.retrieved,
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


class FakeEmbedder(Embedder):
    name = "fake"

    @property
    def dimension(self) -> int:
        return 3

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), float(text.count(" ")), 1.0]


class InMemoryStore(VectorStore):
    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or FakeEmbedder()
        self.points: dict[str, tuple[Chunk, list[float]]] = {}

    def add(self, chunks: list[Chunk]) -> int:
        vectors = self.embedder.embed_documents([c.embedding_text for c in chunks])
        for c, v in zip(chunks, vectors, strict=True):
            self.points[c.point_id] = (c, v)
        return len(chunks)

    def delete_by_doc_id(self, doc_id: str) -> None:
        self.points = {k: p for k, p in self.points.items() if p[0].doc_id != doc_id}

    def search(self, query: str, limit: int) -> list[ScoredChunk]:
        hits = [ScoredChunk(chunk=c, score=1.0) for c, _ in self.points.values()]
        return hits[:limit]
