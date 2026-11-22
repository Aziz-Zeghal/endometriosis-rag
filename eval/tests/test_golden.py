"""The golden sets load, cite only documents of their profile's manifest, and cover every
category, the storyline turns and the routes the guardrail suite checks."""

import pytest
import yaml
from endorag_ingestion.manifest import load_manifest

from eval.golden import load_golden

PATIENT_CATEGORIES = {
    "symptoms",
    "diagnosis",
    "treatment",
    "fertility",
    "daily_life",
    "rights",
    "myth",
    "follow_up",
    "diagnosis_request",
    "prescription_request",
    "not_in_corpus",
    "out_of_scope",
    "chitchat",
    "emergency",
}


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_every_reference_doc_id_is_in_the_manifest(profile):
    enabled = {e.id for e in load_manifest(profile) if e.enabled}
    for item in load_golden(profile):
        assert set(item.reference_doc_ids) <= enabled, item.id


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_lay_and_medical_wordings_are_both_measured(profile):
    wordings = [item.wording for item in load_golden(profile) if item.in_corpus]
    assert wordings.count("lay") >= 3 and wordings.count("medical") >= 3


def test_patient_set_covers_every_category_and_the_storyline():
    items = load_golden("patient")
    assert {item.category for item in items} == PATIENT_CATEGORIES
    assert {f"p-story-{n}" for n in range(1, 9)} <= {item.id for item in items}


def test_gp_set_covers_the_storyline_and_the_guardrails():
    items = load_golden("gp")
    assert {"g-story-9", "g-story-10"} <= {item.id for item in items}
    assert {"emergency", "not_in_corpus", "out_of_scope", "prescription_request"} <= {
        item.category for item in items
    }


def test_unknown_document_is_rejected(tmp_path):
    item = {
        "id": "x",
        "category": "symptoms",
        "wording": "medical",
        "user_input": "?",
        "expected_route": "question",
        "reference_doc_ids": ["no-such-doc"],
        "reference": "…",
    }
    (tmp_path / "patient.yaml").write_text(yaml.safe_dump([item]), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown documents"):
        load_golden("patient", tmp_path)


def test_a_refusal_cannot_cite_documents(tmp_path):
    item = {
        "id": "x",
        "category": "not_in_corpus",
        "user_input": "?",
        "expected_route": "refuse",
        "reference_doc_ids": ["ameli-traitement"],
        "reference": "…",
    }
    (tmp_path / "patient.yaml").write_text(yaml.safe_dump([item]), encoding="utf-8")
    with pytest.raises(ValueError, match="only an in-corpus question"):
        load_golden("patient", tmp_path)
