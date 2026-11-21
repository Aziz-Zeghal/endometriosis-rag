"""Clean-up shared by the converters (`BaseConverter._enrich`) and the chunker.

Structure is cleaned on the DoclingDocument (items removed by label or heading); what remains of the
old Markdown clean-up runs on text: the Markdown snapshot and every chunk's text.
"""

import html
import re

from docling_core.types.doc import DocItemLabel, DoclingDocument, NodeItem

# "12", "- 12 -", "12/30", "Page 12", "Page 12 sur 30", "p. 12"
_PAGE_NUMBER = re.compile(
    r"^\s*(?:-\s*)?(?:page|p\.)?\s*\d{1,3}\s*(?:(?:/|sur|of)\s*\d{1,3})?(?:\s*-)?\s*$", re.I
)
# docling keeps the PDF bullet glyphs after the list marker: "- ● text", "- ■ ■ text".
_BULLET_GLYPHS = re.compile(r"^(\s*[-*] )(?:[●■▪►•◦]\s*)+", re.M)
_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_TOC_LINE = re.compile(r"\.{10,}\s*\d{0,3}\s*$")  # "8.3 Préservation ........ 33"
# A heading that opens the back matter, matched on the whole heading text. Brochures end
# with a contact block (addresses, phone numbers, staff names).
_BACK_MATTER = re.compile(
    r"(?:► )?(?:références(?: bibliographiques)?|references|bibliographie|sources"
    r"|participants|remerciements|acknowledgements|supplementary data"
    r"|contacts?|nous contacter|pour prendre contact avec nous|informations pratiques"
    r"|scannez pour .*)\s*:?",
    re.I,
)
# A heading that opens the related-links block ending a web page (other articles,
# downloads). HTML only: in PDFs such headings ("En savoir plus") start real sections.
_WEB_TRAILER = re.compile(
    r"(?:les autres symptômes|en savoir plus|voir aussi|documents)\s*:?", re.I
)
_ANNEX = re.compile(r"annexe \d+\b", re.I)
_BLANK = "[<>]"  # fill-in field of a report template (HAS imaging guideline annexes)


def clean_document(doc: DoclingDocument) -> DoclingDocument:
    """Remove what retrieval should never return, in place: tables of contents
    (`DOCUMENT_INDEX` items), the back matter and annexes that are blank forms.

    As chunks, these match queries on keywords and carry no content. The back matter
    (references, participants, acknowledgements, contact blocks) starts at its first
    heading and runs to the end of the document. Page headers and footers need no removal:
    docling puts them in the furniture layer, which the Markdown export and the chunker
    leave out.
    """
    items = [item for item, _ in doc.iterate_items()]
    end = _first_heading(items, _BACK_MATTER)
    toc = [item for item in items[:end] if item.label == DocItemLabel.DOCUMENT_INDEX]
    removed = toc + _blank_forms(items[:end]) + items[end:]
    if removed:
        doc.delete_items(node_items=removed)
    return doc


def remove_web_trailer(doc: DoclingDocument) -> DoclingDocument:
    """Remove the related-links block that ends a web page, in place: from the first heading
    such as "Voir aussi" or "Les autres symptômes" to the end of the document."""
    items = [item for item, _ in doc.iterate_items()]
    removed = items[_first_heading(items, _WEB_TRAILER) :]
    if removed:
        doc.delete_items(node_items=removed)
    return doc


def _first_heading(items: list[NodeItem], pattern: re.Pattern) -> int:
    """Index of the first heading matching `pattern` as a whole, or len(items)."""
    matches = (i for i, item in enumerate(items) if _is_heading(item, pattern.fullmatch))
    return next(matches, len(items))


def _is_heading(item: NodeItem, match) -> bool:
    return item.label == DocItemLabel.SECTION_HEADER and bool(match(item.text.strip()))


def _blank_forms(items: list[NodeItem]) -> list[NodeItem]:
    """Items of the annexes (from an "Annexe N" heading to the next) holding a blank field."""
    annexes: list[list[NodeItem]] = []
    for item in items:
        if _is_heading(item, _ANNEX.match):
            annexes.append([])
        if annexes:
            annexes[-1].append(item)
    blank = [annex for annex in annexes if any(_BLANK in getattr(i, "text", "") for i in annex)]
    return [item for annex in blank for item in annex]


def clean_text(text: str) -> str:
    """Reduce links to their text, decode HTML entities, remove bullet glyphs, drop
    dot-leader lines and lines holding only a page number, remove the padding of Markdown
    table rows, collapse blank lines and trim."""
    text = _BULLET_GLYPHS.sub(r"\1", html.unescape(_MD_LINK.sub(r"\1", text)))
    lines = [
        _compact_table_row(line.rstrip())
        for line in text.splitlines()
        if not _TOC_LINE.search(line) and not _PAGE_NUMBER.match(line)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _compact_table_row(line: str) -> str:
    """`| IRM      | 2e |` -> `| IRM | 2e |`: column padding can triple a table's length."""
    if not line.lstrip().startswith("|"):
        return line
    return re.sub(r"-{4,}", "---", re.sub(r" {2,}", " ", line))
