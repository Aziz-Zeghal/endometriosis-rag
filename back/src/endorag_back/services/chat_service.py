"""Chat service: runs the conversation graph for one request and streams its events."""

import logging
import time
from collections.abc import AsyncIterator
from typing import Literal

from endorag_ingestion.core.settings import Profile
from endorag_ingestion.vector_storage import QdrantStore
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.repositories.search_repository import SearchRepository
from endorag_back.services.graph import build_graph_from_settings
from endorag_back.services.state import ChatEvent, TokenEvent

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatService:
    def __init__(self, graph: CompiledStateGraph, profile: Profile, history_messages: int) -> None:
        self._graph = graph
        self._history_messages = history_messages
        self._error_message = load_prompt(profile, "error")
        self._safety_footer = load_prompt(profile, "safety_footer")

    @classmethod
    def from_settings(cls, settings: Settings, store: QdrantStore) -> "ChatService":
        graph = build_graph_from_settings(settings, SearchRepository(store, settings))
        return cls(graph, settings.profile, settings.history_messages)

    def _input_state(self, messages: list[ChatMessage]) -> dict:
        if not messages or messages[-1].role != "user":
            raise ValueError("The last message must come from the user")
        # The latest message plus at most `history_messages` past ones.
        recent = messages[-(self._history_messages + 1) :]
        converted: list[AnyMessage] = [
            HumanMessage(m.content) if m.role == "user" else AIMessage(m.content) for m in recent
        ]
        return {"messages": converted, "query": messages[-1].content}

    async def astream(self, messages: list[ChatMessage]) -> AsyncIterator[ChatEvent]:
        """Route, sources and token events, in the order the nodes write them.

        Only the events the nodes write are streamed (`stream_mode="custom"`): the router's
        JSON and any reasoning never reach the client. Two fixed texts are added here:
        - when a node fails (model or endpoint error, timeout, empty answer, search error),
          the profile's `error` message ends the answer instead of an exception;
        - when the safety LLM check gave no verdict (`source="llm-error"`), the profile's
          `safety_footer` with the emergency numbers ends the answer, whatever the route.
        Each node's duration is logged, then the whole turn's.
        """
        state = self._input_state(messages)
        started = last = time.perf_counter()
        streamed = safety_unchecked = False
        try:
            async for mode, chunk in self._graph.astream(state, stream_mode=["custom", "updates"]):
                if mode == "custom":
                    streamed = streamed or isinstance(chunk, TokenEvent)
                    yield chunk
                    continue
                now = time.perf_counter()
                for node, update in chunk.items():
                    logger.info("Node %s: %.2f s", node, now - last)
                    if node == "safety_gate" and update["emergency"].source == "llm-error":
                        safety_unchecked = True
                last = now
        except Exception:
            logger.exception("Graph failed after %.2f s", time.perf_counter() - started)
            yield TokenEvent(text=("\n\n" if streamed else "") + self._error_message)
        if safety_unchecked:
            yield TokenEvent(text="\n\n" + self._safety_footer)
        logger.info("Turn: %.2f s", time.perf_counter() - started)
