"""Heading-aware Markdown chunker: split on headings, then on size."""

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from endorag_ingestion.core import Chunk, Chunker, ConvertedDocument

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
# Paragraphs, lines, then French sentence and clause boundaries, then words.
SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]


class MarkdownChunker(Chunker):
    """Splits on `#`/`##`/`###` (headings go to `heading_path`), then splits long sections."""

    def __init__(self, chunk_size: int = 1200, overlap: int = 150, min_chars: int = 40) -> None:
        self.min_chars = min_chars
        self._headers = MarkdownHeaderTextSplitter(HEADERS)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=SEPARATORS,
            keep_separator="end",
        )

    def chunk(self, doc: ConvertedDocument) -> list[Chunk]:
        e = doc.entry
        pieces: list[tuple[list[str], str]] = []
        for section in self._headers.split_text(doc.markdown):
            path = [section.metadata[k] for _, k in HEADERS if k in section.metadata]
            if "h1" not in section.metadata:
                path.insert(0, e.title)  # keep the document context on every chunk
            # The header splitter joins lines with "  \n" where the source had a blank line;
            # restore paragraph breaks so the recursive splitter can cut on them.
            content = section.page_content.replace("  \n", "\n\n")
            for text in self._splitter.split_text(content):
                text = text.strip()
                if sum(c.isalnum() for c in text) >= self.min_chars:
                    pieces.append((path, text))
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
                retrieved=doc.retrieved,
                audience=e.audience,
                licence=e.licence,
                format=e.format,
            )
            for i, (path, text) in enumerate(pieces)
        ]
