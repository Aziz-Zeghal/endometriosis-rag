import json
import logging
from pathlib import Path

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, TableCell, TableData
from endorag_ingestion.connectors import HttpConnector
from endorag_ingestion.converters import HtmlConverter, PdfConverter, RoutingConverter, routing
from endorag_ingestion.converters import html as html_converter
from endorag_ingestion.converters.cleaning import clean_document, clean_text
from endorag_ingestion.converters.routing import CONVERTER_VERSION
from endorag_ingestion.core import RawDocument
from endorag_ingestion.manifest import load_entries
from endorag_ingestion.settings import RAW_DIR
from fakes import TODAY, FakeConverter, make_entry

FIXTURES = Path(__file__).parent / "fixtures" / "converters"


class MustNotConvert(FakeConverter):
    def convert(self, raw):
        raise AssertionError(f"{raw.entry.id}: cache miss")


def raw_doc(path: Path, fmt: str = "html", doc_id: str = "doc-a") -> RawDocument:
    return RawDocument(entry=make_entry(doc_id, format=fmt), path=path, retrieved=TODAY)


class CountingConverter(FakeConverter):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def convert(self, raw):
        self.calls += 1
        return super().convert(raw)


def test_html_keeps_headings_and_drops_boilerplate():
    doc = HtmlConverter().convert(raw_doc(FIXTURES / "page.html"))
    md = doc.markdown

    headings = [i.text for i, _ in doc.document.iterate_items() if i.label.endswith("header")]
    assert "Les symptômes" in headings

    assert "# Comprendre l'endométriose" in md.splitlines()
    assert "## Les symptômes" in md.splitlines()
    assert "### Douleurs pendant les règles" in md.splitlines()
    assert "| Antalgiques | Soulager la douleur |" in md  # padding removed
    for boilerplate in ("cookies", "Menu des maladies", "Mentions légales", "tous droits réservés"):
        assert boilerplate not in md


def test_html_keeps_headings_and_text_wrapped_in_buttons():
    md = HtmlConverter().convert(raw_doc(FIXTURES / "accordion.html")).markdown
    lines = md.splitlines()

    assert "# Endométriose : définition et facteurs favorisants" in lines
    assert "## Qu'est-ce que l'endométriose ?" in lines
    assert "## Les facteurs favorisants" in lines
    assert "### Qu'est-ce que l'adénomyose ?" in lines
    assert "L'endométriose est une maladie définie par la présence" in md
    assert "fragments de muqueuse utérine ou tissu endométrial." in md
    assert "Après l'ovulation, la muqueuse utérine s'épaissit" in md


# Long enough to cover most of the fixture's <main> text, so docling is not needed.
RECALL_MD = (
    "# Titre\n\n## Symptômes\n\n" + "Douleurs. " * 100 + "\n\n## Traitements\n\nAntalgiques.\n"
)


def test_html_falls_back_to_recall_when_precision_loses_headings(monkeypatch, caplog):
    calls = []

    def fake_extract(tree, **kwargs):
        calls.append(kwargs.get("favor_recall", False))
        return RECALL_MD if kwargs.get("favor_recall") else None

    monkeypatch.setattr(html_converter.trafilatura, "extract", fake_extract)
    with caplog.at_level(logging.WARNING):
        md = HtmlConverter().convert(raw_doc(FIXTURES / "page.html")).markdown

    assert calls == [False, True]
    assert md.splitlines()[:3] == ["# Titre", "", "## Symptômes"]
    assert "## Traitements" in md.splitlines()
    assert "lost headings or text" not in caplog.text


def test_html_falls_back_to_docling_when_trafilatura_loses_headings(monkeypatch, caplog):
    def fake_extract(tree, **kwargs):
        return "# Titre\n\nTexte."

    monkeypatch.setattr(html_converter.trafilatura, "extract", fake_extract)
    with caplog.at_level(logging.WARNING):
        md = HtmlConverter().convert(raw_doc(FIXTURES / "page.html")).markdown
    assert "lost headings or text" in caplog.text
    assert "## Les symptômes" in md.splitlines()
    assert "cookies" not in md and "Mentions légales" not in md


def test_html_keeps_every_block_of_pages_split_into_content_divs():
    # trafilatura alone keeps only the first `class="content"` block of this page.
    md = HtmlConverter().convert(raw_doc(FIXTURES / "blocks.html")).markdown
    lines = md.splitlines()

    assert "# Trouver la filière Endométriose la plus proche de chez moi" in lines
    for heading in ("Bretagne : Endobreizh", "Occitanie : EndOccitanie", "Pays de Loire : EndoRef"):
        assert f"## {heading}" in lines
    assert "Consulter le site d'Endobreizh" in lines  # links reduced to their text
    for chrome in ("Menu des maladies", "Mentions légales", "utile", "Fermer", "](", "example.org"):
        assert chrome not in md


WIDGETS_HTML = """<html><body><main><article>
<div class="fr-share"><p class="fr-share__title">Partager la page</p></div>
<h1>Reconnaissance de la qualité de travailleur handicapé</h1>
<h2>À quoi sert la RQTH ?</h2>
<p>La RQTH permet de bénéficier d'aménagements du poste de travail et d'un accompagnement
par des organismes spécialisés dans la recherche d'emploi.</p>
<h2>Comment l'obtenir ?</h2>
<p>La demande se fait auprès de la maison départementale des personnes handicapées, avec un
certificat médical de moins d'un an.</p>
<div class="sp-notation sp-no-print"><h2>Cette page vous a-t-elle été utile ?</h2>
<ul><li>1</li><li>2</li><li>3</li></ul><p>Pas du tout</p><p>Parfait !</p></div>
<div class="accordion" id="source-info"><button>A propos de Service Public d'Information</button>
<p>Le Service Public d'Information en Santé associe les institutions publiques.</p></div>
</article></main></body></html>"""


def test_html_drops_share_and_rating_widgets(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(WIDGETS_HTML, encoding="utf-8")
    md = HtmlConverter().convert(raw_doc(page)).markdown

    assert "## Comment l'obtenir ?" in md.splitlines()
    for widget in ("Partager", "utile", "Pas du tout", "Parfait", "Service Public"):
        assert widget not in md


def test_clean_text_reduces_links_to_text_and_decodes_entities():
    text = "En savoir [plus](https://example.org/a).\n\nÂge [&lt;&gt;] ans, voir [ici](/b)."
    assert clean_text(text) == "En savoir plus.\n\nÂge [<>] ans, voir ici."


def test_clean_text_removes_pdf_bullet_glyphs():
    text = "- ● la contraception ;\n- ■ ■ Pas de dépistage.\n  - ▪ sous-point"
    assert clean_text(text) == "- la contraception ;\n- Pas de dépistage.\n  - sous-point"


def test_clean_text_drops_dot_leaders_and_page_numbers():
    text = (
        "Texte.\n12\nPage 3 sur 12\n- 4 -\n5/20\nEn 2026, 12 patientes.\n1. Premier point\n"
        "8.3 Préservation de la fertilité ................................ 33\n\n\n\nFin."
    )
    assert clean_text(text) == "Texte.\nEn 2026, 12 patientes.\n1. Premier point\n\nFin."


def test_clean_document_drops_tables_of_contents_by_label():
    def table(rows: list[list[str]]) -> TableData:
        cells = [
            TableCell(
                text=t,
                start_row_offset_idx=r,
                end_row_offset_idx=r + 1,
                start_col_offset_idx=c,
                end_col_offset_idx=c + 1,
            )
            for r, row in enumerate(rows)
            for c, t in enumerate(row)
        ]
        return TableData(num_rows=len(rows), num_cols=len(rows[0]), table_cells=cells)

    doc = DoclingDocument(name="doc")
    doc.add_heading("Sommaire")
    doc.add_table(
        table([["Généralités", "7"], ["Échographie", "8"]]), label=DocItemLabel.DOCUMENT_INDEX
    )
    doc.add_heading("Imagerie")
    doc.add_table(table([["Examen", "Intention"], ["IRM", "2e"]]))

    md = clean_document(doc).export_to_markdown()
    assert "Généralités" not in md and "Échographie" not in md
    assert "IRM" in md and "Imagerie" in md


def test_clean_text_removes_table_padding():
    text = "| Examen   | Intention   |\n|----------|-------------|\n| IRM      | 2e          |"
    assert clean_text(text) == "| Examen | Intention |\n|---|---|\n| IRM | 2e |"


def test_clean_document_drops_back_matter_to_the_end():
    doc = DoclingDocument(name="doc")
    doc.add_heading("PARTICIPANTS/MATERIALS, SETTING, METHODS")  # not a whole-heading match
    doc.add_text(DocItemLabel.TEXT, "Les traitements hormonaux sont proposés.")
    doc.add_heading("► Participants")
    doc.add_text(DocItemLabel.TEXT, "Dr A, gynécologue, Lyon.")
    doc.add_heading("Abréviations")  # after the back matter starts, everything goes
    doc.add_heading("Références bibliographiques")
    doc.add_list_item("Chapron C. Diagnosing endometriosis. 2019.")

    md = clean_document(doc).export_to_markdown()
    assert "PARTICIPANTS/MATERIALS" in md and "hormonaux" in md
    for back in ("Participants", "Dr A", "Abréviations", "Chapron"):
        assert back not in md


def test_clean_document_drops_annexes_that_are_blank_forms():
    doc = DoclingDocument(name="doc")
    doc.add_heading("Annexe 3. Fiche Information aux patientes")
    doc.add_text(DocItemLabel.TEXT, "L'échographie dure environ trente minutes.")
    doc.add_heading("Annexe 4. Fiche Pratique Echographie pelvienne")
    doc.add_heading("INDICATION")
    doc.add_text(DocItemLabel.TEXT, "Patiente âgée de [<>] ans, examinée à J [<>] du cycle.")
    doc.add_heading("CONCLUSION")
    doc.add_text(DocItemLabel.TEXT, "Absence de lésions d'endométriose décelée.")
    doc.add_heading("Annexe 6. Fiche Technique Protocole IRM")
    doc.add_text(DocItemLabel.TEXT, "A jeun de 3 à 6 h, vessie en semi-réplétion.")

    md = clean_document(doc).export_to_markdown()
    assert "trente minutes" in md and "A jeun" in md
    for form in ("Annexe 4", "INDICATION", "Patiente âgée", "Absence de lésions"):
        assert form not in md


def test_routing_dispatches_on_format_and_writes_cache(tmp_path):
    raw_file = tmp_path / "doc-a.pdf"
    raw_file.write_bytes(b"%PDF fake")
    html, pdf = CountingConverter(), CountingConverter()
    router = RoutingConverter({"html": html, "pdf": pdf}, markdown_dir=tmp_path / "md")

    doc = router.convert(raw_doc(raw_file, fmt="pdf"))

    assert (html.calls, pdf.calls) == (0, 1)
    assert (tmp_path / "md" / "doc-a.md").read_text(encoding="utf-8") == doc.markdown
    cached = DoclingDocument.load_from_json(tmp_path / "md" / "doc-a.docling.json")
    assert cached.export_to_markdown() == doc.document.export_to_markdown()
    meta = json.loads((tmp_path / "md" / "doc-a.meta.json").read_text())
    assert len(meta["source_sha256"]) == 64
    assert meta["converter_version"] == CONVERTER_VERSION


def test_routing_rejects_unknown_format(tmp_path):
    raw_file = tmp_path / "doc-a.html"
    raw_file.write_bytes(b"<html></html>")
    router = RoutingConverter({"html": CountingConverter()}, markdown_dir=tmp_path / "md")
    with pytest.raises(ValueError, match="video"):
        router.convert(raw_doc(raw_file, fmt="video"))


def test_routing_reuses_cache_until_raw_file_changes(tmp_path):
    raw_file = tmp_path / "doc-a.html"
    raw_file.write_bytes(b"<html>v1</html>")
    html = CountingConverter()
    router = RoutingConverter({"html": html}, markdown_dir=tmp_path / "md")

    first = router.convert(raw_doc(raw_file))
    second = router.convert(raw_doc(raw_file))
    assert html.calls == 1
    assert second.markdown == first.markdown
    assert second.document.export_to_dict() == first.document.export_to_dict()

    raw_file.write_bytes(b"<html>v2</html>")
    router.convert(raw_doc(raw_file))
    assert html.calls == 2


def test_routing_redoes_cache_when_converter_version_changes(tmp_path, monkeypatch):
    raw_file = tmp_path / "doc-a.html"
    raw_file.write_bytes(b"<html>v1</html>")
    html = CountingConverter()
    router = RoutingConverter({"html": html}, markdown_dir=tmp_path / "md")

    router.convert(raw_doc(raw_file))
    monkeypatch.setattr(routing, "CONVERTER_VERSION", CONVERTER_VERSION + 1)
    router.convert(raw_doc(raw_file))
    assert html.calls == 2


def test_routing_cache_hit_runs_no_converter(tmp_path):
    raw_file = tmp_path / "doc-a.html"
    raw_file.write_bytes(b"<html>v1</html>")
    RoutingConverter({"html": CountingConverter()}, markdown_dir=tmp_path / "md").convert(
        raw_doc(raw_file)
    )
    (tmp_path / "md" / "doc-a.docling.json").unlink()  # a partial cache is redone
    html = CountingConverter()
    RoutingConverter({"html": html}, markdown_dir=tmp_path / "md").convert(raw_doc(raw_file))
    assert html.calls == 1

    # The default converters are never called on a hit: an offline rebuild needs no docling.
    doc = RoutingConverter(markdown_dir=tmp_path / "md").convert(raw_doc(raw_file))
    assert doc.document.texts[0].text == "Title doc-a"


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_committed_snapshot_is_a_cache_hit_for_every_entry(profile):
    """The offline (Codespace) rebuild converts nothing: re-run the conversion and commit
    data/markdown whenever a raw file or CONVERTER_VERSION changes."""
    # A cache miss raises instead of converting (and overwriting the snapshot).
    router = RoutingConverter({fmt: MustNotConvert() for fmt in ("html", "pdf", "xml")})
    for entry in load_entries(profile):
        raw = HttpConnector(raw_dir=RAW_DIR).fetch(entry)  # cached raw file, no network
        assert router.convert(raw).document.texts, entry.id


@pytest.mark.live  # docling downloads its layout models on first use
def test_pdf_keeps_headings_tables_and_pages():
    doc = PdfConverter().convert(raw_doc(FIXTURES / "sample.pdf", fmt="pdf"))
    md = doc.markdown
    assert all(item.prov for item, _ in doc.document.iterate_items())

    assert "## Diagnostic" in md.splitlines()
    assert "## Prise en charge" in md.splitlines()
    assert "Échographie" in md and "|" in md
