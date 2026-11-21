"""The safety decision and the contract every safety check follows."""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

# medical: acute symptom; psychological: suicidal thoughts or self-harm;
# minor: a child or young person in danger, or violence (119).
EmergencyKind = Literal["medical", "psychological", "minor"]


class SafetyDecision(BaseModel):
    emergency: bool
    kind: EmergencyKind | None = None
    matched: list[str] = []  # labels of the keyword patterns that matched
    # llm-error: the LLM check failed or timed out, so it gave no verdict.
    source: Literal["keyword", "llm", "llm-error"]


class SafetyCheck(ABC):
    """Decides whether the latest user message signals an emergency."""

    @abstractmethod
    async def check(self, text: str) -> SafetyDecision: ...
