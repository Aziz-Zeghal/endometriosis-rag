"""Live storyline helpers: a conversation that keeps its history the way the chat widget
does (each answer is sent back with the next message), and guardrail-level checks."""

import json
import re
import time
from dataclasses import dataclass

from fastapi.testclient import TestClient

# A statement that the user has, or has not, endometriosis. "que vous avez" and "si vous
# avez" are left out: "cela ne signifie pas que vous avez…", "dire si vous avez…".
DIAGNOSIS_STATEMENT = re.compile(
    r"(?<!que )(?<!si )\bvous (avez|n['\u2019]avez pas)\s+(probablement |sûrement |"
    r"certainement |peut-être )?(une |d['\u2019])endométriose",
    re.IGNORECASE,
)
SCORE = re.compile(r"\bscore\s*(de|:)?\s*\d|\b\d+\s*/\s*(10|20|100)\b", re.IGNORECASE)
DOSE = re.compile(r"\b\d+([.,]\d+)?\s*(mg|milligrammes?)\b|\bcomprimés? par jour", re.I)
CITATION = re.compile(r"\[(\d+)\]")


@dataclass
class Turn:
    routes: list[dict]  # data-route payloads, in order
    sources: list[dict]  # data-sources cards
    types: list[str]  # part types, in order
    text: str
    seconds: float

    @property
    def route(self) -> str:
        return self.routes[-1]["route"]  # the part the client keeps

    @property
    def flags(self) -> list[str]:
        return self.routes[-1]["flags"]

    def cited(self) -> set[int]:
        return {int(n) for n in CITATION.findall(self.text)}


class Conversation:
    def __init__(self, client: TestClient, profile: str) -> None:
        self._client = client
        self._profile = profile
        self._messages: list[dict] = []

    def say(self, text: str) -> Turn:
        self._messages.append({"role": "user", "parts": [{"type": "text", "text": text}]})
        body = {"id": "storyline", "messages": self._messages, "profile": self._profile}
        started = time.perf_counter()
        response = self._client.post("/api/chat", json=body)
        seconds = time.perf_counter() - started
        assert response.status_code == 200
        payloads = [line[6:] for line in response.text.split("\n\n") if line]
        assert payloads[-1] == "[DONE]"
        parts = [json.loads(p) for p in payloads[:-1]]
        turn = Turn(
            routes=[p["data"] for p in parts if p["type"] == "data-route"],
            sources=next((p["data"] for p in parts if p["type"] == "data-sources"), []),
            types=[p["type"] for p in parts],
            text="".join(p["delta"] for p in parts if p["type"] == "text-delta"),
            seconds=seconds,
        )
        assert turn.routes and turn.text.strip()
        assert turn.types[0] == "start" and turn.types[-2:] == ["text-end", "finish"]
        self._messages.append({"role": "assistant", "parts": [{"type": "text", "text": turn.text}]})
        print(f"\n[{turn.route} {turn.flags} {seconds:.1f} s] {text}")
        return turn


def assert_cited_answer(turn: Turn, min_sources: int = 2) -> None:
    """A grounded answer: dated sources with links (page links for PDFs), sent before the
    text, and citations that all point to one of them."""
    assert turn.route == "question"
    assert len(turn.sources) >= min_sources
    assert turn.types.index("data-sources") < turn.types.index("text-start")
    for card in turn.sources:
        assert card["date"] and card["url"].startswith("http")
        if card["page"] is not None:
            assert card["url"].endswith(f"#page={card['page']}")
    assert turn.cited(), "no [n] citation in the answer"
    assert turn.cited() <= {card["id"] for card in turn.sources}


def assert_no_sources(turn: Turn) -> None:
    assert "source-url" not in turn.types and "data-sources" not in turn.types
