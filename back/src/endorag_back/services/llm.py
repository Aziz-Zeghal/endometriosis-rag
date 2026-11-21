"""Chat models on the OpenAI-compatible endpoint, removal of inline reasoning, JSON replies."""

import re
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from endorag_back.config.settings import Settings

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def chat_model(settings: Settings, size: Literal["large", "small"], **kwargs: Any) -> ChatOpenAI:
    """`LLM_MODEL` ("large") or `LLM_SMALL_MODEL` ("small"); `kwargs` override the defaults."""
    options: dict[str, Any] = {
        "timeout": settings.llm_timeout_s,
        "reasoning_effort": settings.llm_reasoning_effort or None,  # empty: endpoint default
    } | kwargs
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model if size == "large" else settings.llm_small_model,
        **options,
    )


def strip_reasoning(text: str) -> str:
    """Remove `<think>…</think>` reasoning that some models write inline before the answer.

    Also handles a missing opening tag (everything up to `</think>` is reasoning) and an
    unclosed one (everything from `<think>` on is reasoning).
    """
    text = _THINK_BLOCK.sub("", text)
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    if "<think>" in text:
        text = text.split("<think>", 1)[0]
    return text.strip()


def parse_json_reply[M: BaseModel](text: str, schema: type[M]) -> M:
    """Validate a JSON-mode reply against `schema`, ignoring inline reasoning and any text
    around the outermost `{…}`. Raises `pydantic.ValidationError` when it does not fit."""
    text = strip_reasoning(text)
    start, end = text.find("{"), text.rfind("}")
    return schema.model_validate_json(text[start : end + 1] if 0 <= start < end else text)


class ReasoningFilter:
    """Removes `<think>…</think>` blocks from a token stream, chunk by chunk.

    A tag split across chunks ("<thi" + "nk>") is held back until it can be decided. A stray
    `</think>` (opening tag missing) is dropped; the text before it has already been
    released. Call `flush()` at the end of the stream for the text still held back.
    """

    _OPEN, _CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self._pending = ""
        self._thinking = False

    def feed(self, text: str) -> str:
        self._pending += text
        visible = []
        while True:
            tags = (self._CLOSE,) if self._thinking else (self._OPEN, self._CLOSE)
            found = [(i, tag) for tag in tags if (i := self._pending.find(tag)) >= 0]
            if found:
                index, tag = min(found)
                if not self._thinking:
                    visible.append(self._pending[:index])
                self._pending = self._pending[index + len(tag) :]
                self._thinking = tag == self._OPEN
                continue
            held = max(_partial_tag_length(self._pending, tag) for tag in tags)
            if not self._thinking:
                visible.append(self._pending[: len(self._pending) - held])
            self._pending = self._pending[len(self._pending) - held :]
            return "".join(visible)

    def flush(self) -> str:
        text, self._pending = ("" if self._thinking else self._pending), ""
        return text


def _partial_tag_length(text: str, tag: str) -> int:
    """Length of the longest end of `text` that is a beginning of `tag`."""
    for length in range(min(len(tag) - 1, len(text)), 0, -1):
        if tag.startswith(text[-length:]):
            return length
    return 0
