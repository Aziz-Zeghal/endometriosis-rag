from datetime import date
from itertools import pairwise
from pathlib import Path

from endorag_ingestion.chunkers import MarkdownChunker
from endorag_ingestion.core import ConvertedDocument
from fakes import TODAY, make_entry

FIXTURES = Path(__file__).parent / "fixtures" / "chunker"
TITLE = "Traitement de l'endométriose"


def doc(markdown: str, **kw) -> ConvertedDocument:
    return ConvertedDocument(entry=make_entry(**kw), markdown=markdown, retrieved=TODAY)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_nested_heading_paths():
    chunks = MarkdownChunker().chunk(doc(fixture("nested.md"), title=TITLE))
    assert [c.heading_path for c in chunks] == [
        [TITLE, "Traitements hormonaux"],
        [TITLE, "Traitements hormonaux", "Pilule contraceptive"],
        [TITLE, "Chirurgie"],
    ]
    assert all(not c.text.startswith("#") for c in chunks)


def test_tiny_chunks_dropped_and_indexes_contiguous():
    chunks = MarkdownChunker().chunk(doc(fixture("nested.md"), title=TITLE))
    assert all("Sommaire" not in c.text for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_no_h1_gets_manifest_title():
    chunks = MarkdownChunker().chunk(doc(fixture("no_h1.md"), title="Endométriose"))
    assert [c.heading_path for c in chunks] == [
        ["Endométriose", "Symptômes"],
        ["Endométriose", "Diagnostic"],
    ]


def test_long_section_split_with_overlap():
    sentences = [
        f"La phrase numéro {i} décrit un symptôme fréquent de la maladie." for i in range(40)
    ]
    markdown = "# Titre\n\n## Long\n\n" + " ".join(sentences)
    chunks = MarkdownChunker(chunk_size=300, overlap=80).chunk(doc(markdown))
    assert len(chunks) > 3
    assert all(len(c.text) <= 300 for c in chunks)
    assert all(c.heading_path == ["Titre", "Long"] for c in chunks)
    for prev, nxt in pairwise(chunks):
        first_sentence = nxt.text.split(". ")[0]
        assert first_sentence in prev.text  # consecutive chunks share text
    # Cuts happen at sentence ends, not mid-word.
    assert all(c.text.endswith(".") for c in chunks)


def test_payload_fields_copied():
    entry_kw = dict(
        doc_id="has-pdf",
        title=TITLE,
        source="HAS",
        published=None,
        checked=date(2026, 3, 2),
        audience="gp",
        format="pdf",
        licence="etalab-2.0",
    )
    (c,) = MarkdownChunker().chunk(doc(fixture("no_h1.md").split("## Diagnostic")[0], **entry_kw))
    assert c.doc_id == "has-pdf"
    assert c.source == "HAS"
    assert c.title == TITLE
    assert c.url == "https://example.org/has-pdf"
    assert c.published == date(2026, 3, 2)
    assert c.retrieved == TODAY
    assert c.audience == "gp"
    assert c.format == "pdf"
    assert c.licence == "etalab-2.0"
    assert c.start_seconds is None
