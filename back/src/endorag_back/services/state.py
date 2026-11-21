"""Graph state, the decisions of the classification nodes and the events streamed to the API."""

from datetime import date
from typing import Literal

from endorag_ingestion.core import ScoredChunk
from langchain_core.messages import AnyMessage
from pydantic import BaseModel
from typing_extensions import TypedDict

from endorag_back.services.safety import SafetyDecision

Flag = Literal["asks_for_diagnosis", "asks_for_prescription"]


class RouteDecision(BaseModel):
    """The router's verdict on the latest user message."""

    route: Literal["chitchat", "out_of_scope", "question"]
    asks_for_diagnosis: bool = False  # explicit or implicit ("c'est normal ?")
    asks_for_prescription: bool = False  # dose or treatment choice for a person

    @property
    def flags(self) -> list[Flag]:
        return [f for f in ("asks_for_diagnosis", "asks_for_prescription") if getattr(self, f)]


class TriageDecision(BaseModel):
    """Weak evidence: ask a precise question, or decline (not in the sources)."""

    decision: Literal["clarify", "refuse"]


class Citation(BaseModel):
    """A source passed to `generate`; `index` is the number cited in the answer ([1], [2]…)."""

    index: int
    doc_id: str
    title: str
    source: str  # publishing organisation
    url: str  # with `#page=N` for PDF chunks
    published: date
    page: int | None = None


class ChatState(TypedDict, total=False):
    messages: list[AnyMessage]  # past turns, then the latest user message
    query: str  # text of the latest user message
    emergency: SafetyDecision
    route: RouteDecision
    search_query: str  # standalone query written by `rewrite`
    chunks: list[ScoredChunk]
    sufficient: bool  # evidence verdict of `retrieve`
    triage: Literal["clarify", "refuse"]
    answer: str
    citations: list[Citation]


# Events written by the nodes with `get_stream_writer()`, streamed by the chat service.


class RouteEvent(BaseModel):
    type: Literal["route"] = "route"
    route: Literal["emergency", "chitchat", "out_of_scope", "question", "clarify", "refuse"]
    flags: list[Flag] = []  # set by the router, repeated by triage


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    sources: list[Citation]


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


ChatEvent = RouteEvent | SourcesEvent | TokenEvent
