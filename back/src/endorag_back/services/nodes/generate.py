"""Generate: the cited answer, only from the numbered passages, streamed after its sources."""

from endorag_ingestion.core import ScoredChunk
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from endorag_back.services.nodes.streaming import stream_answer
from endorag_back.services.state import ChatState, Citation, SourcesEvent

# Markers read by the generate prompt, which says how to answer each request.
DIAGNOSIS_MARKER = "[demande de diagnostic]"
PRESCRIPTION_MARKER = "[demande de prescription]"


def citations(chunks: list[ScoredChunk]) -> list[Citation]:
    return [
        Citation(
            index=i,
            doc_id=hit.chunk.doc_id,
            title=hit.chunk.title,
            source=hit.chunk.source,
            url=hit.chunk.citation_url,
            published=hit.chunk.published,
            page=hit.chunk.page,
        )
        for i, hit in enumerate(chunks, start=1)
    ]


def passages_message(state: ChatState) -> str:
    """The numbered passages, then the user's message and the request markers."""
    blocks = []
    for i, hit in enumerate(state["chunks"], start=1):
        c = hit.chunk
        header = f"[{i}] {c.source}, « {c.title} », {c.published.isoformat()}"
        if c.page is not None:
            header += f", page {c.page}"
        section = f"\nSection : {' > '.join(c.heading_path)}" if c.heading_path else ""
        blocks.append(f"{header}{section}\n{c.text}")
    parts = ["Passages :", "\n\n".join(blocks), f"Message de l'utilisateur :\n{state['query']}"]
    if state["search_query"] != state["query"]:
        parts.append(f"Question reformulée :\n{state['search_query']}")
    route = state["route"]
    markers = [
        marker
        for flag, marker in (
            (route.asks_for_diagnosis, DIAGNOSIS_MARKER),
            (route.asks_for_prescription, PRESCRIPTION_MARKER),
        )
        if flag
    ]
    if markers:
        parts.append(" ".join(markers))
    return "\n\n".join(parts)


def make_generate_node(model: BaseChatModel, system_prompt: str):
    async def generate_node(state: ChatState) -> dict:
        sources = citations(state["chunks"])
        get_stream_writer()(SourcesEvent(sources=sources))
        messages = [SystemMessage(system_prompt), HumanMessage(passages_message(state))]
        return {"answer": await stream_answer(model, messages), "citations": sources}

    return generate_node
