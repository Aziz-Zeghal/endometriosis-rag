"""Safety check by a small chat model: catches the phrasings the keyword list misses."""

import asyncio
import logging
from typing import get_args

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, field_validator

from endorag_back.services.llm import parse_json_reply
from endorag_back.services.safety.base import EmergencyKind, SafetyCheck, SafetyDecision

logger = logging.getLogger(__name__)


class _Verdict(BaseModel):
    emergency: bool
    kind: EmergencyKind | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def _unknown_kind_is_none(cls, value: object) -> object:
        # An unexpected label ("suicidal", "Medical") must not lose an emergency verdict.
        return value if value in get_args(EmergencyKind) else None


class LlmSafetyCheck(SafetyCheck):
    """Asks `model` for a JSON verdict (the schema is in `system_prompt`).

    Never raises: on a timeout, an endpoint error or an unparsable reply it returns
    `emergency=False` with `source="llm-error"`, so the other checks decide.
    """

    def __init__(self, model: BaseChatModel, system_prompt: str, timeout_s: float) -> None:
        self._model = model.bind(response_format={"type": "json_object"})
        self._system_prompt = system_prompt
        self._timeout_s = timeout_s

    async def check(self, text: str) -> SafetyDecision:
        messages = [SystemMessage(self._system_prompt), HumanMessage(text)]
        try:
            reply = await asyncio.wait_for(self._model.ainvoke(messages), self._timeout_s)
            verdict = parse_json_reply(reply.text, _Verdict)
        except Exception as exc:
            # The user's message is not logged.
            logger.warning("LLM safety check failed (%s)", type(exc).__name__)
            return SafetyDecision(emergency=False, source="llm-error")
        return SafetyDecision(
            emergency=verdict.emergency,
            kind=verdict.kind if verdict.emergency else None,
            source="llm",
        )
