"""HTML to Markdown with trafilatura: main content only, headings kept as `#` lines."""

import copy
import logging
import re
from io import BytesIO

import trafilatura
from lxml import etree
from trafilatura.utils import load_html

from endorag_ingestion.converters.cleaning import clean_markdown
from endorag_ingestion.core import ConvertedDocument, Converter, RawDocument

logger = logging.getLogger(__name__)

_MD_HEADING = re.compile(r"^#{1,6} ", re.M)
# Page widgets, matched on class tokens: share buttons, "was this page useful?" ratings
# and blocks the site itself hides when printing.
_WIDGET_CLASS = r"(^|[\s_-])(share|feedback|notation|no-print)([\s_-]|$)"
_WIDGETS = f"//*[re:test(@class, '{_WIDGET_CLASS}', 'i')]"
# Also dropped before the docling fallback, which keeps everything it is given.
_CHROME = ".//nav|.//aside|.//form|.//img|.//picture|.//figure"
_NS = {"re": "http://exslt.org/regular-expressions"}


class HtmlConverter(Converter):
    """Drops navigation, footers and cookie banners; keeps headings, paragraphs and tables.

    Extraction runs in precision mode first. If that loses most headings or most of the
    text, it runs again in recall mode, which some pages (Inserm) need to keep their
    structure. If both lose them, the page's `<main>` is converted with docling's HTML
    backend: trafilatura keeps only the first block matching its content selectors, which
    drops pages split into many `class="content"` blocks (Santé.fr filières).
    """

    def convert(self, raw: RawDocument) -> ConvertedDocument:
        tree = load_html(raw.path.read_bytes())
        if tree is None:
            raise ValueError(f"{raw.entry.id}: could not parse HTML")
        # trafilatura drops <button> with its text: unwrap it to keep accordion headings
        # (`<h2><button>Title</button></h2>`) and inline glossary terms.
        etree.strip_tags(tree, "button")
        for el in tree.xpath(_WIDGETS, namespaces=_NS):
            el.drop_tree()
        expected = _html_heading_count(tree)
        main = next(iter(tree.xpath("//main")), None)
        main_chars = len(" ".join(main.text_content().split())) if main is not None else 0

        def poor(md: str) -> bool:
            return _md_heading_count(md) * 2 < expected or len(md) * 2 < main_chars

        markdown = _extract(tree, favor_precision=True)
        if poor(markdown):
            markdown = _extract(tree, favor_recall=True)
        if poor(markdown):
            logger.warning("%s: trafilatura lost headings or text", raw.entry.id)
            if main is not None:
                markdown = _docling(main)
        if not markdown:
            raise ValueError(f"{raw.entry.id}: no content extracted")
        return ConvertedDocument(
            entry=raw.entry, markdown=clean_markdown(markdown), retrieved=raw.retrieved
        )


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


def _docling(main: etree._Element) -> str:
    """Convert one element with docling's HTML backend (no models)."""
    from docling.datamodel.base_models import DocumentStream, InputFormat
    from docling.document_converter import DocumentConverter

    main = copy.deepcopy(main)
    for el in main.xpath(_CHROME):
        el.drop_tree()
    html = b"<html><body>" + etree.tostring(main, encoding="utf-8") + b"</body></html>"
    stream = DocumentStream(name="page.html", stream=BytesIO(html))
    doc = DocumentConverter(allowed_formats=[InputFormat.HTML]).convert(stream).document
    return doc.export_to_markdown(image_placeholder="")


def _html_heading_count(tree: etree._Element) -> int:
    """h1-h3 tags in <main> when the page has one, else in the whole page."""
    root = next(iter(tree.xpath("//main")), tree)
    return len(root.xpath(".//h1|.//h2|.//h3"))


def _md_heading_count(markdown: str) -> int:
    return len(_MD_HEADING.findall(markdown))
