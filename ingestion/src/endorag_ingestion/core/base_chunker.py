"""Base classes for chunking strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
from docling_core.types.doc import DocItemLabel, DoclingDocument, InlineGroup, TextItem

from endorag_ingestion.core.cleaning import clean_text
from endorag_ingestion.core.models import Chunk, ConvertedDocument

if TYPE_CHECKING:
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, document: ConvertedDocument) -> list[Chunk]:
        """Split a converted document into retrievable chunks carrying its citation metadata."""


class _MarkdownTables(ChunkingSerializerProvider):
    """Serialize tables as Markdown tables. The default "row, header = cell" triplets take
    the first row as the header and repeat it in every row of two-column glossaries."""

    def get_serializer(self, doc):
        return ChunkingDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer())


def _is_text_of(parent) -> bool:
    return isinstance(parent, InlineGroup) or (isinstance(parent, TextItem) and not parent.text)


def _join_inline_runs(document: DoclingDocument) -> DoclingDocument:
    """A copy where each paragraph with mixed formatting (an inline group) is one text item.

    `HybridChunker` re-joins the runs of such a paragraph with newlines
    ("une \\n**endométriose**\\n, un"). An inline group that is the whole text of its parent
    (a list item, a heading) is serialized whole already and stays as it is.
    """
    doc = document.model_copy(deep=True)
    serializer = ChunkingDocSerializer(doc=doc)
    groups = [
        item
        for item, _ in doc.iterate_items(with_groups=True)
        if isinstance(item, InlineGroup) and not _is_text_of(item.parent.resolve(doc))
    ]
    for group in groups:
        runs = [ref.resolve(doc) for ref in group.children]
        prov = next((p for run in runs for p in getattr(run, "prov", [])), None)
        text = serializer.serialize(item=group).text
        doc.insert_text(group, label=DocItemLabel.TEXT, text=text, prov=prov, after=False)
    if groups:
        doc.delete_items(node_items=groups)
    return doc


class BaseHybridChunker(BaseChunker):
    """BaseChunker backed by docling's `HybridChunker`.

    The chunker follows the DoclingDocument's structure (sections, paragraphs, list items,
    tables kept as Markdown tables), splits pieces that exceed `max_tokens` of the embedder's
    tokenizer (headings included) and merges small neighbours under the same headings. Chunk
    text is then cleaned and chunks with fewer than `min_chars` letters and digits are dropped.

    Each chunk keeps its context the way docling's `contextualize()` does, but as metadata:
    `heading_path` (the manifest title first) and the page of its first item. The heading
    path is prepended to the text only when embedding (`Chunk.embedding_text`).

    `tokenizer` is a Hugging Face model id, loaded on first use, or a ready tokenizer.
    Subclasses may add modality-specific chunks on top of _text_chunks().
    """

    def __init__(
        self, tokenizer: "str | BaseTokenizer", max_tokens: int = 512, min_chars: int = 40
    ) -> None:
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.min_chars = min_chars
        self._chunker: HybridChunker | None = None

    @property
    def chunker(self) -> "HybridChunker":
        """docling's HybridChunker, built on first use (the tokenizer may be downloaded)."""
        if self._chunker is None:
            from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
            from docling_core.transforms.chunker.tokenizer.huggingface import (
                HuggingFaceTokenizer,
            )

            tokenizer = self.tokenizer
            if isinstance(tokenizer, str):
                tokenizer = HuggingFaceTokenizer.from_pretrained(
                    tokenizer, max_tokens=self.max_tokens
                )
            self._chunker = HybridChunker(
                tokenizer=tokenizer, merge_peers=True, serializer_provider=_MarkdownTables()
            )
        return self._chunker

    def _text_chunks(self, document: ConvertedDocument) -> list[Chunk]:
        """Text chunks with their heading path, page and the entry's citation metadata."""
        e = document.entry
        titles = {
            item.text
            for item, _ in document.document.iterate_items()
            if item.label == DocItemLabel.TITLE
        }
        pieces: list[tuple[list[str], str, int | None]] = []
        for c in self.chunker.chunk(dl_doc=_join_inline_runs(document.document)):
            text = clean_text(c.text)
            if sum(ch.isalnum() for ch in text) < self.min_chars:
                continue
            path = list(c.meta.headings or [])
            if not path or path[0] not in titles:
                path.insert(0, e.title)  # keep the document context on every chunk
            page = next((p.page_no for item in c.meta.doc_items for p in item.prov), None)
            pieces.append((path, text, page))
        return [
            Chunk(
                doc_id=e.id,
                chunk_index=i,
                text=text,
                heading_path=path,
                source=e.source,
                title=e.title,
                url=str(e.url),
                published=e.citation_date,
                retrieved=document.retrieved,
                audience=e.audience,
                licence=e.licence,
                format=e.format,
                page=page,
            )
            for i, (path, text, page) in enumerate(pieces)
        ]

    def chunk(self, document: ConvertedDocument) -> list[Chunk]:
        """Default chunking is text only."""
        return self._text_chunks(document)
