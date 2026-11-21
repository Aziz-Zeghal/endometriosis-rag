"""Deterministic stand-ins for the chat models and the search repository, and a graph runner."""

from datetime import date

from endorag_back.prompts import load_prompt
from endorag_back.repositories.search_repository import Retrieval
from endorag_back.services.graph import build_graph
from endorag_back.services.safety import CompositeSafetyCheck, KeywordSafetyCheck, LlmSafetyCheck
from endorag_ingestion.core import Chunk, ScoredChunk
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

NODES_WITH_MODEL = ["safety_gate", "router", "rewrite", "triage", "clarify", "generate"]


class ScriptedChatModel(BaseChatModel):
    """Replies per node, the node being recognised by its system prompt; records every call.

    `replies[node]` is the reply text (default: `default_reply`); a node in `errors` raises.
    Streaming yields the reply in pieces of `piece_size` characters.
    """

    prompts: dict[str, str]  # system prompt -> node
    replies: dict[str, str] = Field(default_factory=dict)
    errors: set[str] = Field(default_factory=set)
    default_reply: str = "Réponse."
    piece_size: int = 5
    calls: list[tuple[str, list[BaseMessage]]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _reply(self, messages: list[BaseMessage]) -> str:
        node = self.prompts.get(messages[0].text, "unknown")
        self.calls.append((node, messages))
        if node in self.errors:
            raise RuntimeError(f"{node} failed")
        return self.replies.get(node, self.default_reply)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError  # the graph is async

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(self._reply(messages)))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        text = self._reply(messages)
        for i in range(0, len(text), self.piece_size):
            yield ChatGenerationChunk(message=AIMessageChunk(text[i : i + self.piece_size]))

    def nodes_called(self) -> list[str]:
        return [node for node, _ in self.calls]

    def messages_of(self, node: str) -> list[BaseMessage]:
        return next(messages for n, messages in self.calls if n == node)


class FakeRepository:
    def __init__(self, retrieval: Retrieval) -> None:
        self.retrieval = retrieval
        self.queries: list[str] = []

    def retrieve(self, query: str) -> Retrieval:
        self.queries.append(query)
        return self.retrieval


def scored(
    doc_id: str,
    text: str,
    dense: float,
    published: date = date(2025, 1, 1),
    page: int | None = None,
) -> ScoredChunk:
    chunk = Chunk(
        doc_id=doc_id,
        chunk_index=0,
        text=text,
        heading_path=["Endométriose"],
        source="Organisme",
        title=f"Titre {doc_id}",
        url=f"https://example.org/{doc_id}" + (".pdf" if page else ""),
        published=published,
        retrieved=date(2026, 11, 21),
        audience="patient",
        licence="all-rights-reserved",
        format="pdf" if page else "html",
        page=page,
    )
    return ScoredChunk(chunk=chunk, score=0.03, dense_score=dense)


STRONG = Retrieval(
    chunks=[
        scored("recent", "Une douleur qui perturbe la vie quotidienne fait consulter.", 0.7),
        scored("guide", "L'échographie est l'examen de base.", 0.6, date(2017, 12, 1), page=4),
    ],
    best_dense_score=0.7,
    sufficient=True,
)
WEAK = Retrieval(
    chunks=[scored("far", "Texte sans rapport avec la question.", 0.2)],
    best_dense_score=0.2,
    sufficient=False,
)


def models(profile: str, **small_kw) -> tuple[ScriptedChatModel, ScriptedChatModel]:
    """(large, small) models that recognise the prompts of `profile`."""
    prompts = {load_prompt(profile, node): node for node in NODES_WITH_MODEL}
    small_kw.setdefault("replies", {})
    small_kw["replies"].setdefault("safety_gate", '{"emergency": false, "kind": null}')
    return ScriptedChatModel(prompts=prompts), ScriptedChatModel(prompts=prompts, **small_kw)


def graph_for(profile, repo, large, small):
    safety = CompositeSafetyCheck(
        [KeywordSafetyCheck(profile), LlmSafetyCheck(small, load_prompt(profile, "safety_gate"), 1)]
    )
    return build_graph(profile, safety, repo, large, small)


def conversation(*texts: str) -> dict:
    """Input state from alternating user / assistant texts, the last one from the user."""
    messages = [HumanMessage(t) if i % 2 == 0 else AIMessage(t) for i, t in enumerate(texts[::-1])][
        ::-1
    ]
    return {"messages": messages, "query": texts[-1]}


async def run(graph, state: dict) -> tuple[list[str], list, dict]:
    """(nodes run in order, custom events, merged final state)."""
    path, events, final = [], [], dict(state)
    async for mode, chunk in graph.astream(state, stream_mode=["updates", "custom"]):
        if mode == "custom":
            events.append(chunk)
            continue
        for node, update in chunk.items():
            path.append(node)
            final.update(update or {})
    return path, events, final
