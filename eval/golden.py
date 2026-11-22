"""Load and validate the golden sets (`eval/golden/<profile>.yaml`)."""

from pathlib import Path
from typing import Literal

import yaml
from endorag_back.services.state import Flag
from endorag_ingestion.core.settings import Profile
from endorag_ingestion.manifest import load_manifest
from pydantic import BaseModel, model_validator

GOLDEN_DIR = Path(__file__).parent / "golden"

Category = Literal[
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
]
# The route the client keeps (last `data-route` part): the router's, or triage's decision.
Route = Literal["emergency", "chitchat", "out_of_scope", "question", "clarify", "refuse"]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GoldenItem(BaseModel):
    id: str
    category: Category
    user_input: str
    history: list[Message] = []  # earlier turns, for follow-ups
    expected_route: Route
    expected_flags: list[Flag] = []
    reference_doc_ids: list[str] = []
    reference: str
    wording: Literal["lay", "medical"] | None = None  # set on every in-corpus question

    @property
    def in_corpus(self) -> bool:
        """A question answered from the corpus: the retrieval and RAGAS subset."""
        return self.expected_route == "question" and bool(self.reference_doc_ids)

    @model_validator(mode="after")
    def _consistent(self) -> "GoldenItem":
        if self.expected_route == "question" and self.category != "not_in_corpus":
            if not self.reference_doc_ids or self.wording is None:
                raise ValueError(f"{self.id}: a question needs reference_doc_ids and wording")
        elif self.reference_doc_ids:
            raise ValueError(f"{self.id}: only an in-corpus question cites documents")
        if self.history and self.history[-1].role != "assistant":
            raise ValueError(f"{self.id}: history must end with an assistant turn")
        return self


def load_golden(profile: Profile, golden_dir: Path = GOLDEN_DIR) -> list[GoldenItem]:
    """Every item of a profile's golden set. Ids are unique and every cited document is in
    the profile's manifest."""
    path = golden_dir / f"{profile}.yaml"
    items = [GoldenItem.model_validate(raw) for raw in yaml.safe_load(path.read_text("utf-8"))]
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate ids")
    known = {entry.id for entry in load_manifest(profile) if entry.enabled}
    for item in items:
        if unknown := set(item.reference_doc_ids) - known:
            raise ValueError(f"{path}: {item.id} cites unknown documents {sorted(unknown)}")
    return items
