"""LLM safety check, composite and fixed emergency messages, with a fake chat model."""

import asyncio
import re
import time

import pytest
from endorag_back.prompts import PROMPTS_DIR, load_prompt
from endorag_back.services.safety import (
    CompositeSafetyCheck,
    KeywordSafetyCheck,
    LlmSafetyCheck,
    SafetyDecision,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeChatModel(BaseChatModel):
    """Replies `reply` after `delay` seconds, or raises `error`; counts its calls."""

    reply: str = '{"emergency": false, "kind": null}'
    delay: float = 0.0
    error: str | None = None
    calls: int = 0
    last_kwargs: dict | None = None

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError  # the checks are async only

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        await asyncio.sleep(self.delay)
        if self.error:
            raise RuntimeError(self.error)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(self.reply))])


def llm_check(model: FakeChatModel, timeout_s: float = 1.0) -> LlmSafetyCheck:
    return LlmSafetyCheck(model, load_prompt("patient", "safety_gate"), timeout_s)


NORMAL = "J'ai super mal pendant mes règles, c'est normal ?"
EMERGENCY = "J'ai envie que tout s'arrête."
INDIRECT = "Je ne vois plus l'intérêt de continuer."  # not in the keyword list


# LlmSafetyCheck


@pytest.mark.asyncio
async def test_llm_check_reads_the_json_verdict_in_json_mode():
    model = FakeChatModel(reply='<think>…</think>{"emergency": true, "kind": "psychological"}')
    decision = await llm_check(model).check(INDIRECT)
    assert decision == SafetyDecision(emergency=True, kind="psychological", source="llm")
    assert model.last_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ['"suicidal"', '"Medical"', "3"])
async def test_llm_check_keeps_an_emergency_with_an_unknown_kind(kind):
    model = FakeChatModel(reply=f'{{"emergency": true, "kind": {kind}}}')
    decision = await llm_check(model).check(INDIRECT)
    assert decision == SafetyDecision(emergency=True, source="llm")


@pytest.mark.asyncio
async def test_llm_check_drops_the_kind_of_a_non_emergency():
    model = FakeChatModel(reply='{"emergency": false, "kind": "medical"}')
    decision = await llm_check(model).check(NORMAL)
    assert decision == SafetyDecision(emergency=False, source="llm")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        FakeChatModel(error="endpoint down"),
        FakeChatModel(delay=5),
        FakeChatModel(reply="Je ne peux pas répondre."),
        FakeChatModel(reply='{"emergency": "peut-être"}'),
    ],
    ids=["error", "timeout", "not-json", "bad-schema"],
)
async def test_llm_check_never_raises(model):
    start = time.perf_counter()
    decision = await llm_check(model, timeout_s=0.05).check(EMERGENCY)
    assert decision == SafetyDecision(emergency=False, source="llm-error")
    assert time.perf_counter() - start < 1


# CompositeSafetyCheck


@pytest.mark.asyncio
async def test_composite_short_circuits_on_a_keyword_hit():
    model = FakeChatModel(delay=5)
    gate = CompositeSafetyCheck([KeywordSafetyCheck("patient"), llm_check(model, timeout_s=10)])
    start = time.perf_counter()
    decision = await gate.check(EMERGENCY)
    assert time.perf_counter() - start < 0.3
    assert model.calls == 0
    assert decision.emergency
    assert decision.source == "keyword"
    assert decision.kind == "psychological"


@pytest.mark.asyncio
async def test_composite_asks_the_llm_when_keywords_miss():
    model = FakeChatModel(reply='{"emergency": true, "kind": "psychological"}')
    gate = CompositeSafetyCheck([KeywordSafetyCheck("patient"), llm_check(model)])
    decision = await gate.check(INDIRECT)
    assert model.calls == 1
    assert decision == SafetyDecision(emergency=True, kind="psychological", source="llm")


@pytest.mark.asyncio
async def test_composite_safe_when_no_check_triggers():
    model = FakeChatModel()
    gate = CompositeSafetyCheck([KeywordSafetyCheck("patient"), llm_check(model)])
    decision = await gate.check(NORMAL)
    assert decision == SafetyDecision(emergency=False, source="llm")


@pytest.mark.asyncio
async def test_llm_failure_keeps_the_keyword_verdict():
    model = FakeChatModel(error="endpoint down")
    gate = CompositeSafetyCheck([KeywordSafetyCheck("patient"), llm_check(model)])
    assert (await gate.check(NORMAL)) == SafetyDecision(emergency=False, source="llm-error")
    # Even when the failing check runs first, the keyword check still triggers.
    gate = CompositeSafetyCheck([llm_check(model), KeywordSafetyCheck("patient")])
    decision = await gate.check(EMERGENCY)
    assert decision.emergency
    assert decision.source == "keyword"


def test_composite_needs_a_check():
    with pytest.raises(ValueError):
        CompositeSafetyCheck([])


# Fixed emergency messages


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_emergency_message_gives_every_number(profile):
    message = load_prompt(profile, "emergency")
    for number in ["15", "112", "114", "3114", "119", "116 117"]:
        assert re.search(rf"(?<!\d){number}(?!\d)", message), number
    assert "SMS" in message
    assert "<!--" not in message  # returned verbatim: no authoring comments


def test_emergency_message_wording_differs_by_profile():
    assert load_prompt("patient", "emergency") != load_prompt("gp", "emergency")
    assert (PROMPTS_DIR / "patient" / "emergency.md").read_text().startswith("Ce que vous décrivez")
