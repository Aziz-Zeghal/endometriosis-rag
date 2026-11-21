"""In-memory fakes for every pipeline interface (offline tests)."""

from datetime import date
from pathlib import Path

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
        body = "\n\n".join(f"Paragraph {i} of {raw.entry.id}." for i in range(self.paragraphs))
        return ConvertedDocument(
            entry=raw.entry, markdown=f"# {raw.entry.title}\n\n{body}", retrieved=raw.retrieved
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
    def __init__(self) -> None:
        self.points: dict[str, tuple[Chunk, list[float]]] = {}

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        for c, v in zip(chunks, vectors, strict=True):
            self.points[c.point_id] = (c, v)
        return len(chunks)

    def delete_by_doc_id(self, doc_id: str) -> None:
        self.points = {k: p for k, p in self.points.items() if p[0].doc_id != doc_id}

    def search(self, query: str, query_vector: list[float], limit: int) -> list[ScoredChunk]:
        hits = [ScoredChunk(chunk=c, score=1.0) for c, _ in self.points.values()]
        return hits[:limit]
