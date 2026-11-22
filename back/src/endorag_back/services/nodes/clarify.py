"""Clarify: one precise follow-up question, streamed."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from endorag_back.services.nodes.history import transcript
from endorag_back.services.nodes.streaming import stream_answer
from endorag_back.services.state import ChatState


def make_clarify_node(model: BaseChatModel, system_prompt: str):
    async def clarify_node(state: ChatState) -> dict:
        # One labelled transcript, not chat turns: given the turns, the model answered the
        # user's question (« Oui, c'est possible ») instead of asking one (eval guardrails).
        human = HumanMessage(transcript(state["messages"]))
        answer = await stream_answer(model, [SystemMessage(system_prompt), human])
        return {"answer": answer}

    return clarify_node
