"""HTML to a DoclingDocument: trafilatura extracts the main content as Markdown (headings
kept as `#` lines), then docling's Markdown backend parses it."""

import copy
import logging
import re
from io import BytesIO

import trafilatura
from docling_core.types.doc import DoclingDocument
from lxml import etree
from trafilatura.utils import load_html

from endorag_ingestion.converter.cleaning import CleaningConverter, clean_text, remove_web_trailer
from endorag_ingestion.core import RawDocument

logger = logging.getLogger(__name__)

_MD_HEADING = re.compile(r"^#{1,6} ", re.M)
# Indented text that is not a list item: Markdown would make it a code block. A list
# marker alone on its line takes the indented text that follows.
_INDENTED_TEXT = re.compile(r"^[ \t]+(?=\S)(?![-*+] |\d+\. )", re.M)
_BARE_MARKER = re.compile(r"^([ \t]*(?:[-*+]|\d+\.))[ \t]*\n[ \t]+(?=\S)", re.M)
# Page widgets, matched on class tokens: share buttons, "was this page useful?" ratings,
# blocks the site itself hides when printing, tables of contents ("Sommaire") and Santé.fr's
# content-type label; plus Santé.fr's "about the publisher" box and tooltips (Service-Public
# glossary tooltips hold a "titleContent" placeholder).
_WIDGET_CLASS = r"(^|[\s_-])(share|feedback|notation|no-print|btn-summary|content-type)([\s_-]|$)"
_WIDGETS = (
    f"//*[re:test(@class, '{_WIDGET_CLASS}', 'i')] | //*[@id='source-info'] | //*[@role='tooltip']"
)
# Also dropped before the docling fallback, which keeps everything it is given.
_CHROME = ".//nav|.//aside|.//form|.//img|.//picture|.//figure"
_NS = {"re": "http://exslt.org/regular-expressions"}


class HtmlConverter(CleaningConverter):
    """Drops navigation, footers and cookie banners; keeps headings, paragraphs and tables.

    Extraction runs in precision mode first. If that loses most headings or most of the
    text, it runs again in recall mode, which some pages (Inserm) need to keep their
    structure. If both lose them, the page's `<main>` is converted with docling's HTML
    backend: trafilatura keeps only the first block matching its content selectors, which
    drops pages split into many `class="content"` blocks (Santé.fr filières).

    The fallback stays in _parse rather than _repair: it is not a failure to recover from
    but a quality check on a successful extraction, and it reuses the parsed page.
    Either way the result is a DoclingDocument, chunked like the PDFs; HTML has no pages.
    Pages without `<main>` use the block around the `<h1>` that holds most headings.
    """

    def _parse(self, raw: RawDocument) -> DoclingDocument:
        tree = load_html(raw.path.read_bytes())
        if tree is None:
            raise ValueError(f"{raw.entry.id}: could not parse HTML")
        for el in tree.xpath(_WIDGETS, namespaces=_NS):
            el.drop_tree()
        # trafilatura drops <button> with its text: unwrap it to keep accordion headings
        # (`<h2><button>Title</button></h2>`) and inline glossary terms.
        etree.strip_tags(tree, "button")
        main = next(iter(tree.xpath("//main")), None)
        root = main if main is not None else _title_block(tree)
        expected = _html_heading_count(tree if root is None else root)
        main_chars = len(" ".join(main.text_content().split())) if main is not None else 0

        def poor(md: str) -> bool:
            return _md_heading_count(md) * 2 < expected or len(md) * 2 < main_chars

        markdown = _extract(tree, favor_precision=True)
        if poor(markdown):
            markdown = _extract(tree, favor_recall=True)
        if poor(markdown):
            logger.warning("%s: trafilatura lost headings or text", raw.entry.id)
            if root is not None:
                return _docling_main(root)
        if not markdown:
            raise ValueError(f"{raw.entry.id}: no content extracted")
        markdown = _INDENTED_TEXT.sub("", _BARE_MARKER.sub(r"\1 ", markdown))
        return to_docling(clean_text(markdown).encode(), "page.md")

    def _enrich(self, document: DoclingDocument) -> None:
        """Also remove the related-links block that ends the page."""
        super()._enrich(remove_web_trailer(document))


def _extract(tree: etree._Element, **mode: bool) -> str:
    return (
        trafilatura.extract(
            copy.deepcopy(tree),
            output_format="markdown",
            include_tables=True,
            include_links=False,
            include_images=False,
            include_comments=False,
            **mode,
        )
        or ""
    )


def to_docling(content: bytes, filename: str) -> DoclingDocument:
    """Parse HTML or Markdown (format from the file extension) with docling. No models."""
    from docling.datamodel.base_models import DocumentStream, InputFormat
    from docling.document_converter import DocumentConverter

    stream = DocumentStream(name=filename, stream=BytesIO(content))
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML, InputFormat.MD])
    return converter.convert(stream).document


def _docling_main(main: etree._Element) -> DoclingDocument:
    """Convert the page's <main> with docling's HTML backend, chrome removed."""
    main = copy.deepcopy(main)
    for el in main.xpath(_CHROME):
        el.drop_tree()
    html = b"<html><body>" + etree.tostring(main, encoding="utf-8") + b"</body></html>"
    return to_docling(html, "page.html")


def _title_block(tree: etree._Element) -> etree._Element | None:
    """For pages without `<main>` (CHUV): the nearest ancestor of the `<h1>` holding at
    least half of the page's h1-h3 headings."""
    total = _html_heading_count(tree)
    for h1 in tree.xpath("//h1")[:1]:
        for block in h1.iterancestors():
            if _html_heading_count(block) * 2 >= total:
                return block
    return None


def _html_heading_count(root: etree._Element) -> int:
    return len(root.xpath(".//h1|.//h2|.//h3"))


def _md_heading_count(markdown: str) -> int:
    return len(_MD_HEADING.findall(markdown))
