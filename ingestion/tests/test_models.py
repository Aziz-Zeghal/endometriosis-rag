import pytest
from fakes import FakeChunker, FakeConnector, FakeConverter, make_entry
from pydantic import ValidationError


def test_entry_requires_a_date():
    with pytest.raises(ValidationError, match="published' or 'checked"):
        make_entry(published=None)


def test_entry_accepts_checked_date_only():
    from datetime import date

    e = make_entry(published=None, checked=date(2026, 10, 15))
    assert e.citation_date == date(2026, 10, 15)


def test_entry_rejects_bad_id_and_format():
    with pytest.raises(ValidationError):
        make_entry("Bad Id")
    with pytest.raises(ValidationError):
        make_entry(format="docx")


def test_point_id_is_stable_and_unique():
    entry = make_entry()
    doc = FakeConverter(paragraphs=3).convert(FakeConnector().fetch(entry))
    chunks = FakeChunker().chunk(doc)
    again = FakeChunker().chunk(doc)
    assert [c.point_id for c in chunks] == [c.point_id for c in again]
    assert len({c.point_id for c in chunks}) == 3


def test_embedding_text_has_headings_but_no_metadata():
    entry = make_entry()
    chunk = FakeChunker().chunk(FakeConverter().convert(FakeConnector().fetch(entry)))[0]
    assert chunk.embedding_text.startswith(entry.title)
    assert str(entry.url) not in chunk.embedding_text
