"""Rewrite: a standalone search query from the latest message and the past turns."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from endorag_back.services.llm import strip_reasoning
from endorag_back.services.nodes.history import transcript
from endorag_back.services.state import ChatState

logger = logging.getLogger(__name__)


def make_rewrite_node(model: BaseChatModel, system_prompt: str):
    async def rewrite_node(state: ChatState) -> dict:
        history = state["messages"][:-1]
        if not history:
            return {"search_query": state["query"]}
        human = HumanMessage(transcript(state["messages"]))
        try:
            reply = await model.ainvoke([SystemMessage(system_prompt), human])
            query = strip_reasoning(reply.text)
        except Exception as exc:
            logger.warning("Rewrite failed (%s), searching the raw message", type(exc).__name__)
            query = ""
        return {"search_query": query or state["query"]}

    return rewrite_node
