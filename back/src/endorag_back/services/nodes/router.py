"""Router: chitchat, out_of_scope or question, plus the diagnosis and prescription flags."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from endorag_back.services.llm import parse_json_reply
from endorag_back.services.nodes.history import transcript
from endorag_back.services.state import ChatState, RouteDecision, RouteEvent

logger = logging.getLogger(__name__)


def make_router_node(model: BaseChatModel, system_prompt: str):
    json_model = model.bind(response_format={"type": "json_object"})

    async def router_node(state: ChatState) -> dict:
        # Past turns are included so a follow-up ("et pour la fertilité ?") is a question.
        human = HumanMessage(transcript(state["messages"]))
        try:
            reply = await json_model.ainvoke([SystemMessage(system_prompt), human])
            decision = parse_json_reply(reply.text, RouteDecision)
        except Exception as exc:
            # A question goes through retrieval and grounded generation: the safe default.
            logger.warning("Router failed (%s), routing to question", type(exc).__name__)
            decision = RouteDecision(route="question")
        logger.info("Router: %s", decision.model_dump())
        get_stream_writer()(RouteEvent(route=decision.route, flags=decision.flags))
        return {"route": decision}

    return router_node
