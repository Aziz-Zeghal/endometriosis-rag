from datetime import date
from pathlib import Path

import pytest
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    Formatting,
    ProvenanceItem,
)
from endorag_ingestion.chunker import HybridChunker
from endorag_ingestion.converter.cleaning import clean_text
from endorag_ingestion.converter.html import to_docling
from endorag_ingestion.core import ConvertedDocument
from endorag_ingestion.core.settings import Settings
from fakes import TODAY, WordTokenizer, make_entry

FIXTURES = Path(__file__).parent / "fixtures" / "chunker"
TITLE = "Traitement de l'endométriose"


def doc(markdown: str, **kw) -> ConvertedDocument:
    """A ConvertedDocument parsed from Markdown by docling's Markdown backend (offline)."""
    document = to_docling(markdown.encode(), "doc.md")
    return ConvertedDocument(
        entry=make_entry(**kw), document=document, markdown=markdown, retrieved=TODAY
    )


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def chunker(max_tokens: int = 64) -> HybridChunker:
    """Wired like the factory: chunk text goes through the converters' text clean-up."""
    return HybridChunker(WordTokenizer(max_tokens=max_tokens), text_cleaner=clean_text)


def test_nested_heading_paths():
    chunks = chunker().chunk(doc(fixture("nested.md"), title=TITLE))
    assert [c.heading_path for c in chunks] == [
        [TITLE, "Traitements hormonaux"],
        [TITLE, "Traitements hormonaux", "Pilule contraceptive"],
        [TITLE, "Chirurgie"],
    ]
    assert all(not c.text.startswith("#") for c in chunks)


def test_tiny_chunks_dropped_and_indexes_contiguous():
    chunks = chunker().chunk(doc(fixture("nested.md"), title=TITLE))
    assert all("Sommaire" not in c.text for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_no_title_gets_manifest_title():
    chunks = chunker().chunk(doc(fixture("no_h1.md"), title="Endométriose"))
    assert [c.heading_path for c in chunks] == [
        ["Endométriose", "Symptômes"],
        ["Endométriose", "Diagnostic"],
    ]


def test_long_section_split_under_max_tokens():
    sentences = [
        f"La phrase numéro {i} décrit un symptôme fréquent de la maladie." for i in range(40)
    ]
    markdown = "# Titre\n\n## Long\n\n" + " ".join(sentences)
    tokenizer = WordTokenizer(max_tokens=60)
    chunks = HybridChunker(tokenizer).chunk(doc(markdown))
    assert len(chunks) > 3
    # The budget covers the headings too, as in HybridChunker.contextualize.
    assert all(tokenizer.count_tokens("Titre\nLong\n" + c.text) <= 60 for c in chunks)
    assert all(c.heading_path == ["Titre", "Long"] for c in chunks)
    assert " ".join(c.text for c in chunks) == " ".join(sentences)  # nothing lost
    assert all(c.text.endswith(".") for c in chunks)  # cuts at sentence ends


def test_small_paragraphs_under_one_heading_are_merged():
    markdown = "# Titre\n\n## Section\n\n" + "\n\n".join(
        f"Le paragraphe {i} donne une information utile aux patientes." for i in range(4)
    )
    (c,) = chunker().chunk(doc(markdown))
    assert c.text.count("paragraphe") == 4


def test_chunk_text_is_cleaned():
    markdown = (
        "# Titre\n\n## Section\n\n"
        "- ● la contraception estroprogestative en continu ;\n"
        "- ■ ■ un dispositif intra-utérin hormonal, selon l'avis du médecin.\n\n"
        "12\n\nAnnexe .................................................. 33\n"
    )
    (c,) = chunker().chunk(doc(markdown))
    assert c.text == (
        "- la contraception estroprogestative en continu ;\n"
        "- un dispositif intra-utérin hormonal, selon l'avis du médecin."
    )


def test_paragraph_with_formatting_stays_one_line():
    markdown = (
        "# Titre\n\n## Section\n\nSi vous avez une **endométriose**, un suivi (*voir* "
        "[ici](https://example.org)) est utile.\n\n- une **liste**, avec du gras\n"
    )
    original = doc(markdown)
    (c,) = chunker().chunk(original)
    assert c.text == (
        "Si vous avez une **endométriose**, un suivi (*voir* ici) est utile.\n"
        "- une **liste**, avec du gras"
    )
    assert len(original.document.groups) == 3  # the converted document is left unchanged


def test_formatted_paragraph_nested_under_heading_stays_one_line():
    """docling's JATS backend puts a section's paragraphs under its heading item."""
    document = DoclingDocument(name="jats")
    heading = document.add_heading("Diagnosis")
    group = document.add_inline_group(parent=heading)
    document.add_text(DocItemLabel.TEXT, "Both approaches are equivalent (Chapron ", parent=group)
    document.add_text(DocItemLabel.TEXT, "et al.", parent=group, formatting=Formatting(italic=True))
    document.add_text(DocItemLabel.TEXT, ", 1998).", parent=group)
    converted = ConvertedDocument(
        entry=make_entry(title=TITLE), document=document, markdown="", retrieved=TODAY
    )
    (c,) = chunker().chunk(converted)
    assert c.heading_path == [TITLE, "Diagnosis"]
    assert c.text == "Both approaches are equivalent (Chapron *et al.*, 1998)."


GLOSSARY = "# Titre\n\n## Abréviations\n\n| AINS | Anti-inflammatoires non stéroïdiens |\n" + (
    "| --- | --- |\n"
    + "".join(f"| ABR{i} | Définition numéro {i} de l'abréviation |\n" for i in range(30))
)


def test_tables_stay_markdown_tables_without_repeated_first_row():
    chunks = chunker(max_tokens=80).chunk(doc(GLOSSARY))
    assert len(chunks) > 1  # the table is split
    for c in chunks:
        lines = c.text.splitlines()
        assert all(line.startswith("|") for line in lines)
        assert lines[0].startswith("| AINS ")  # each piece is a valid table, header first
        assert set(lines[1]) <= set("|- ")  # then the separator row
        assert c.text.count("Anti-inflammatoires") == 1  # not repeated on every row
    rows = [line for c in chunks for line in c.text.splitlines() if "ABR" in line]
    assert len(rows) == 30


def pdf_document() -> DoclingDocument:
    """A small PDF-like document: items carry their page number."""

    def prov(page: int, text: str) -> ProvenanceItem:
        bbox = BoundingBox(l=0, t=0, r=100, b=10)
        return ProvenanceItem(page_no=page, bbox=bbox, charspan=(0, len(text)))

    document = DoclingDocument(name="has-pdf")
    texts = [
        (DocItemLabel.SECTION_HEADER, "Diagnostic", 2),
        (DocItemLabel.TEXT, "L'échographie pelvienne est l'examen de première intention.", 2),
        (DocItemLabel.SECTION_HEADER, "Traitement", 3),
        (DocItemLabel.TEXT, "Les traitements hormonaux sont proposés en première intention.", 3),
    ]
    for label, text, page in texts:
        if label == DocItemLabel.SECTION_HEADER:
            document.add_heading(text, prov=prov(page, text))
        else:
            document.add_text(label=label, text=text, prov=prov(page, text))
    return document


ENTRY_KW = dict(
    doc_id="has-pdf",
    title=TITLE,
    source="HAS",
    published=None,
    checked=date(2026, 3, 2),
    audience="gp",
    format="pdf",
    licence="etalab-2.0",
)


def test_payload_fields_and_pdf_pages():
    converted = ConvertedDocument(
        entry=make_entry(**ENTRY_KW), document=pdf_document(), markdown="", retrieved=TODAY
    )
    first, second = chunker().chunk(converted)
    assert first.heading_path == [TITLE, "Diagnostic"]
    assert (first.page, second.page) == (2, 3)
    assert first.citation_url == "https://example.org/has-pdf#page=2"
    assert first.doc_id == "has-pdf"
    assert first.source == "HAS"
    assert first.title == TITLE
    assert first.url == "https://example.org/has-pdf"
    assert first.published == date(2026, 3, 2)
    assert first.retrieved == TODAY
    assert first.audience == "gp"
    assert first.format == "pdf"
    assert first.licence == "etalab-2.0"
    assert first.start_seconds is None


def test_html_chunks_have_no_page():
    (c, *_) = chunker().chunk(doc(fixture("no_h1.md")))
    assert c.page is None
    assert c.citation_url == c.url


@pytest.mark.live  # downloads the embedder's tokenizer from Hugging Face on first use
def test_real_tokenizer_keeps_chunks_under_max_tokens():
    settings = Settings(_env_file=None)
    sentences = [f"La phrase {i} décrit la dysménorrhée et la dyspareunie." for i in range(300)]
    markdown = "# Titre\n\n## Long\n\n" + " ".join(sentences)
    chunks = HybridChunker(settings.chunk_tokenizer, max_tokens=128).chunk(doc(markdown))
    tokenizer = HuggingFaceTokenizer.from_pretrained(settings.chunk_tokenizer)
    assert len(chunks) > 5
    assert all(tokenizer.count_tokens("Titre\nLong\n" + c.text) <= 128 for c in chunks)
