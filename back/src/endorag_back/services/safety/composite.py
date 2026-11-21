"""Runs safety checks in order; the first one that triggers decides."""

from collections.abc import Sequence

from endorag_back.services.safety.base import SafetyCheck, SafetyDecision


class CompositeSafetyCheck(SafetyCheck):
    """`CompositeSafetyCheck([KeywordSafetyCheck(profile), LlmSafetyCheck(...)])`.

    The checks run one after the other and the first emergency is returned at once, so a
    keyword hit never waits for the model. When none triggers, the last decision is returned
    (with the LLM last, `source="llm-error"` tells the caller that check gave no verdict).
    A failing check returns a non-emergency decision instead of raising, so it never stops
    the others.
    """

    def __init__(self, checks: Sequence[SafetyCheck]) -> None:
        if not checks:
            raise ValueError("CompositeSafetyCheck needs at least one check")
        self._checks = list(checks)

    async def check(self, text: str) -> SafetyDecision:
        for safety_check in self._checks:
            decision = await safety_check.check(text)
            if decision.emergency:
                return decision
        return decision
