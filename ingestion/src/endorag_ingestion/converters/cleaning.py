"""Markdown clean-up shared by the converters."""

import html
import re

_HEADING = re.compile(r"^(#{1,6})(?:\s+(.*?))?\s*#*\s*$")
# "12", "- 12 -", "12/30", "Page 12", "Page 12 sur 30", "p. 12"
_PAGE_NUMBER = re.compile(
    r"^\s*(?:-\s*)?(?:page|p\.)?\s*\d{1,3}\s*(?:(?:/|sur|of)\s*\d{1,3})?(?:\s*-)?\s*$", re.I
)


# docling keeps the PDF bullet glyphs after the list marker: "- ● text", "- ■ ■ text".
_BULLET_GLYPHS = re.compile(r"^(\s*[-*] )(?:[●■▪►•◦]\s*)+", re.M)
_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_TOC_ROW = re.compile(r"\.{5,}|\|\s*\d{1,3}\s*\|\s*$")
_TOC_LINE = re.compile(r"\.{10,}\s*\d{0,3}\s*$")  # "8.3 Préservation ........ 33"


def strip_page_numbers(markdown: str) -> str:
    """Drop lines that only hold a page number (PDF headers and footers)."""
    return "\n".join(line for line in markdown.splitlines() if not _PAGE_NUMBER.match(line))


def clean_markdown(markdown: str) -> str:
    """Drop empty and trailing headings and tables of contents, reduce links to their text,
    decode HTML entities, remove bullet glyphs, collapse blank lines and trim the result."""
    markdown = html.unescape(_MD_LINK.sub(r"\1", markdown))
    lines = _drop_toc_tables(_BULLET_GLYPHS.sub(r"\1", markdown).splitlines())
    kept: list[str] = []
    for i, line in enumerate(lines):
        if _TOC_LINE.search(line):
            continue
        heading = _HEADING.match(line)
        if heading and (not heading.group(2) or _only_headings_follow(lines, i)):
            continue
        kept.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n"


def _only_headings_follow(lines: list[str], index: int) -> bool:
    """True if no text follows the heading before the end of the document.

    A heading directly followed by another heading of the same level is kept: docling
    flattens PDF headings to `##`, so it is often a real section with subsections.
    """
    return all(not line.strip() or _HEADING.match(line) for line in lines[index + 1 :])


def _drop_toc_tables(lines: list[str]) -> list[str]:
    """Drop Markdown tables whose rows mostly end with a page number or dot leaders.

    docling turns a PDF table of contents into such a table; as a chunk it matches every
    query on keywords and carries no content.
    """
    kept: list[str] = []
    table: list[str] = []
    for line in [*lines, ""]:
        if line.lstrip().startswith("|"):
            table.append(line)
            continue
        rows = [r for r in table if not re.fullmatch(r"[\s|:-]+", r)]
        if not rows or sum(bool(_TOC_ROW.search(r)) for r in rows) * 2 < len(rows):
            kept.extend(table)
        table = []
        kept.append(line)
    return kept[:-1]
