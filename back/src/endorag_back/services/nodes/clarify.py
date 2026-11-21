"""Clarify: one precise follow-up question, streamed."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

from endorag_back.services.nodes.streaming import stream_answer
from endorag_back.services.state import ChatState


def make_clarify_node(model: BaseChatModel, system_prompt: str):
    async def clarify_node(state: ChatState) -> dict:
        answer = await stream_answer(model, [SystemMessage(system_prompt), *state["messages"]])
        return {"answer": answer}

    return clarify_node
