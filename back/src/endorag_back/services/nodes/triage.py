"""Triage, on weak evidence: clarify (an ambiguous question) or refuse (not in the sources)."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from endorag_back.services.llm import parse_json_reply
from endorag_back.services.state import ChatState, RouteEvent, TriageDecision

logger = logging.getLogger(__name__)

_SNIPPETS = 3  # closest passages shown to the model
_SNIPPET_CHARS = 300


def make_triage_node(model: BaseChatModel, system_prompt: str):
    json_model = model.bind(response_format={"type": "json_object"})

    async def triage_node(state: ChatState) -> dict:
        snippets = "\n".join(
            f"- {hit.chunk.title} : {hit.chunk.text[:_SNIPPET_CHARS]}"
            for hit in state.get("chunks", [])[:_SNIPPETS]
        )
        human = (
            f"Question :\n{state['search_query']}\n\n"
            f"Passages les plus proches (jugés insuffisants) :\n{snippets or '(aucun)'}"
        )
        try:
            reply = await json_model.ainvoke([SystemMessage(system_prompt), HumanMessage(human)])
            decision = parse_json_reply(reply.text, TriageDecision).decision
        except Exception as exc:
            # Grounded or silent: without a verdict, decline rather than guess.
            logger.warning("Triage failed (%s), refusing", type(exc).__name__)
            decision = "refuse"
        logger.info("Triage: %s", decision)
        # The client keeps only the latest `data-route` part: carry the router's flags.
        get_stream_writer()(RouteEvent(route=decision, flags=state["route"].flags))
        return {"triage": decision}

    return triage_node
