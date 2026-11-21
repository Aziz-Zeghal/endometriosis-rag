from pathlib import Path

import httpx
import pytest
from endorag_ingestion.manifest import load_entries, load_manifest
from endorag_ingestion.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures" / "manifests"
EXCLUDED_HOSTS = ("cngof.fr", "info-endometriose")


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_manifest_loads_with_unique_ids_and_dates(profile):
    entries = load_manifest(profile)
    ids = [e.id for e in entries]
    assert entries
    assert len(ids) == len(set(ids))
    assert all(e.citation_date for e in entries)


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_excluded_publishers_absent(profile):
    for entry in load_manifest(profile):
        assert not any(host in str(entry.url) for host in EXCLUDED_HOSTS), entry.id


def test_patient_corpus_has_about_25_enabled_entries():
    enabled = load_entries("patient")
    assert 20 <= len(enabled) <= 30
    assert "inserm-dossier" not in {e.id for e in enabled}


def test_ameli_entries_have_crawl_delay():
    ameli = [e for e in load_manifest("patient") if e.source == "Ameli"]
    assert ameli
    assert all(e.crawl_delay_s == 10 for e in ameli)


def test_shared_entries_are_identical_in_both_manifests():
    patient = {e.id: e for e in load_manifest("patient")}
    gp = {e.id: e for e in load_manifest("gp")}
    shared = set(patient) & set(gp)
    assert shared == {e.id for e in patient.values() if e.audience == "both"}
    assert shared == {e.id for e in gp.values() if e.audience == "both"}
    assert all(patient[i] == gp[i] for i in shared)


def test_only_selects_ids_even_if_disabled():
    entries = load_entries("patient", only=["inserm-dossier", "sp-ald"])
    assert [e.id for e in entries] == ["sp-ald", "inserm-dossier"]


def test_only_rejects_unknown_ids():
    with pytest.raises(ValueError, match="introuvable"):
        load_entries("patient", only=["introuvable"])


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate id 'doc-a'"):
        load_manifest("duplicate", FIXTURES)


def test_undated_entry_is_rejected():
    with pytest.raises(ValueError, match="needs a 'published' or 'checked' date"):
        load_manifest("undated", FIXTURES)


@pytest.mark.live
@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_enabled_urls_answer_200(profile):
    """An enabled entry the connector cannot fetch is silently skipped by the pipeline."""
    headers = {"User-Agent": Settings().user_agent}
    with httpx.Client(follow_redirects=True, timeout=60, headers=headers) as client:
        failures = {
            e.id: status
            for e in load_entries(profile)
            if (status := client.get(str(e.url)).status_code) != 200
        }
    assert not failures


def test_only_forces_disabled_entries_on():
    from endorag_ingestion.manifest import load_entries

    entries = load_entries("patient", only=["inserm-dossier"])
    assert [e.enabled for e in entries] == [True]
