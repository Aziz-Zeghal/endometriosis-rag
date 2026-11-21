import pytest
from endorag_back.config.settings import Settings
from endorag_back.services.llm import (
    ReasoningFilter,
    chat_model,
    parse_json_reply,
    strip_reasoning,
)
from pydantic import BaseModel, ValidationError


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bonjour.", "Bonjour."),
        ("<think>raisonnement\nsur deux lignes</think>\n\nRéponse.", "Réponse."),
        ("<think>a</think>Début <think>b</think>fin.", "Début fin."),
        ("raisonnement sans balise ouvrante</think>Réponse.", "Réponse."),
        ("Réponse.<think>raisonnement jamais fermé", "Réponse."),
        ("<think>tout est raisonnement</think>", ""),
    ],
)
def test_strip_reasoning(text, expected):
    assert strip_reasoning(text) == expected


def test_chat_model_sizes_and_overrides():
    s = Settings(
        _env_file=None,
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
        llm_timeout_s=42,
    )
    large = chat_model(s, "large")
    assert large.model_name == "large-model"
    assert large.request_timeout == 42
    assert str(large.openai_api_base) == "http://llm.test/v1"
    small = chat_model(s, "small", timeout=5, temperature=0)
    assert small.model_name == "small-model"
    assert small.request_timeout == 5
    assert small.temperature == 0
    assert large.reasoning_effort is None  # the endpoint's default unless configured


def test_chat_model_sends_the_configured_reasoning_effort():
    s = Settings(
        _env_file=None,
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
        llm_reasoning_effort="none",
    )
    for size in ("large", "small"):
        payload = chat_model(s, size)._get_request_payload("Bonjour")
        assert payload["reasoning_effort"] == "none"
        assert "reasoning" not in payload  # stays on Chat Completions
    s.llm_reasoning_effort = ""  # `LLM_REASONING_EFFORT=` left empty in .env
    assert "reasoning_effort" not in chat_model(s, "large")._get_request_payload("Bonjour")


class Verdict(BaseModel):
    emergency: bool


@pytest.mark.parametrize(
    "text",
    [
        '{"emergency": true}',
        '<think>raisonnement</think>\n{"emergency": true}',
        'Voici le JSON : ```json\n{"emergency": true}\n```',
    ],
)
def test_parse_json_reply(text):
    assert parse_json_reply(text, Verdict) == Verdict(emergency=True)


@pytest.mark.parametrize("text", ["", "pas de JSON", '{"emergency": "peut-être"}'])
def test_parse_json_reply_rejects_what_does_not_fit(text):
    with pytest.raises(ValidationError):
        parse_json_reply(text, Verdict)


@pytest.mark.parametrize(
    "pieces",
    [
        ["<think>raisonnement</think>Réponse [1]."],
        ["<thi", "nk>raison", "nement</th", "ink>Rép", "onse [1]."],
        list("<think>r</think>Réponse [1]."),
        ["Répo", "<think>caché</think>", "nse [1]."],
    ],
)
def test_reasoning_filter_hides_think_blocks_split_across_chunks(pieces):
    reasoning = ReasoningFilter()
    visible = "".join(reasoning.feed(p) for p in pieces) + reasoning.flush()
    assert visible == "Réponse [1]."


def test_reasoning_filter_releases_a_lone_angle_bracket_at_the_end():
    reasoning = ReasoningFilter()
    assert reasoning.feed("a < b et c <") == "a < b et c "
    assert reasoning.flush() == "<"


def test_reasoning_filter_drops_an_unclosed_block():
    reasoning = ReasoningFilter()
    assert reasoning.feed("Réponse.<think>jamais fermé") == "Réponse."
    assert reasoning.flush() == ""


def test_reasoning_filter_drops_a_stray_closing_tag():
    reasoning = ReasoningFilter()
    pieces = ["raisonnement caché</th", "ink>Réponse [1]."]
    visible = "".join(reasoning.feed(p) for p in pieces) + reasoning.flush()
    assert "</think>" not in visible
    assert visible.endswith("Réponse [1].")
