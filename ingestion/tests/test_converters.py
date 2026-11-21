import json
import logging
from pathlib import Path

import pytest
from endorag_ingestion.converters import HtmlConverter, PdfConverter, RoutingConverter, routing
from endorag_ingestion.converters import html as html_converter
from endorag_ingestion.converters.cleaning import clean_markdown, strip_page_numbers
from endorag_ingestion.converters.routing import CONVERTER_VERSION
from endorag_ingestion.core import RawDocument
from fakes import TODAY, FakeConverter, make_entry

FIXTURES = Path(__file__).parent / "fixtures" / "converters"


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
    md = HtmlConverter().convert(raw_doc(FIXTURES / "page.html")).markdown

    assert "# Comprendre l'endométriose" in md.splitlines()
    assert "## Les symptômes" in md.splitlines()
    assert "### Douleurs pendant les règles" in md.splitlines()
    assert "| Antalgiques | Soulager la douleur |" in md
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
    assert md == clean_markdown(RECALL_MD)
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
</article></main></body></html>"""


def test_html_drops_share_and_rating_widgets(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(WIDGETS_HTML, encoding="utf-8")
    md = HtmlConverter().convert(raw_doc(page)).markdown

    assert "## Comment l'obtenir ?" in md.splitlines()
    for widget in ("Partager", "utile", "Pas du tout", "Parfait"):
        assert widget not in md


def test_clean_markdown():
    md = "# Titre\n\n\n\n## \n\nTexte.\n\n## Section\n\nContenu.\n\n### Fin vide\n\n#### Fin\n"
    assert clean_markdown(md) == "# Titre\n\nTexte.\n\n## Section\n\nContenu.\n"


def test_clean_markdown_keeps_section_heading_followed_by_same_level_heading():
    md = "## GÉNÉRALITÉS\n\n## Évolution\n\nTexte.\n"
    assert clean_markdown(md) == md


def test_clean_markdown_reduces_links_to_text_and_decodes_entities():
    md = "## [En savoir plus](https://example.org/a)\n\nÂge [&lt;&gt;] ans, voir [ici](/b).\n"
    assert clean_markdown(md) == "## En savoir plus\n\nÂge [<>] ans, voir ici.\n"


def test_clean_markdown_removes_pdf_bullet_glyphs():
    md = "- ● la contraception ;\n- ■ ■ Pas de dépistage.\n  - ▪ sous-point\n"
    assert clean_markdown(md) == "- la contraception ;\n- Pas de dépistage.\n  - sous-point\n"


def test_clean_markdown_drops_tables_of_contents_only():
    toc = (
        "## Sommaire\n\n| 1. | Généralités | 7 |\n|----|----|----|\n"
        "| 2. | Échographie | 8 |\n| Préambule ........ | | |\n\n"
        "8.3 Préservation de la fertilité ................................ 33\n\n"
    )
    data = "| Examen | Intention |\n|---|---|\n| Échographie | 1re |\n| IRM | 2e |\n"
    md = clean_markdown(toc + "## Imagerie\n\n" + data)
    for toc_entry in ("Généralités", "Préambule", "Préservation"):
        assert toc_entry not in md
    assert data in md


def test_strip_page_numbers():
    md = "Texte.\n12\nPage 3 sur 12\n- 4 -\n5/20\nEn 2026, 12 patientes.\n1. Premier point"
    assert strip_page_numbers(md) == "Texte.\nEn 2026, 12 patientes.\n1. Premier point"


def test_routing_dispatches_on_format_and_writes_cache(tmp_path):
    raw_file = tmp_path / "doc-a.pdf"
    raw_file.write_bytes(b"%PDF fake")
    html, pdf = CountingConverter(), CountingConverter()
    router = RoutingConverter({"html": html, "pdf": pdf}, markdown_dir=tmp_path / "md")

    doc = router.convert(raw_doc(raw_file, fmt="pdf"))

    assert (html.calls, pdf.calls) == (0, 1)
    assert (tmp_path / "md" / "doc-a.md").read_text(encoding="utf-8") == doc.markdown
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


@pytest.mark.live  # docling downloads its layout models on first use
def test_pdf_keeps_headings_and_tables():
    md = PdfConverter().convert(raw_doc(FIXTURES / "sample.pdf", fmt="pdf")).markdown

    assert "## Diagnostic" in md.splitlines()
    assert "## Prise en charge" in md.splitlines()
    assert "Échographie" in md and "|" in md
