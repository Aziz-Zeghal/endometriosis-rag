"""Streams a chat model's answer to the API as token events, without inline reasoning."""

from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.config import get_stream_writer

from endorag_back.services.llm import ReasoningFilter
from endorag_back.services.state import TokenEvent


class EmptyAnswerError(RuntimeError):
    """The model returned no visible text (only reasoning, or nothing)."""


async def stream_answer(model: BaseChatModel, messages: Sequence[BaseMessage]) -> str:
    """Write each visible chunk as a `TokenEvent` and return the streamed text.

    Only the message text is read: reasoning returned in a separate field is never streamed.
    The returned answer is exactly what was streamed, stripped. Raises `EmptyAnswerError`
    when nothing visible came out, so the chat service sends its fallback message.
    """
    write = get_stream_writer()
    reasoning = ReasoningFilter()
    parts: list[str] = []
    async for chunk in model.astream(messages):
        visible = reasoning.feed(chunk.text)
        if not parts:  # whitespace left before the answer by a reasoning block is skipped
            visible = visible.lstrip()
        if visible:
            parts.append(visible)
            write(TokenEvent(text=visible))
    if rest := reasoning.flush():
        rest = rest if parts else rest.lstrip()
        if rest:
            parts.append(rest)
            write(TokenEvent(text=rest))
    answer = "".join(parts).strip()
    if not answer:
        raise EmptyAnswerError("The model returned no visible answer")
    return answer
