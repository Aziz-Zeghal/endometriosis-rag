"""Run golden items through the real conversation graph of one profile, in process.

The graph is built exactly as the API builds it (`build_graph_from_settings`, real models,
real index); `ainvoke` returns the final state, so the route, flags, retrieved chunks and
answer of each turn can be scored. One profile at a time: local Qdrant locks its directory,
so the backend must not be running.
"""

import asyncio
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from endorag_back.config.settings import Settings
from endorag_back.repositories.search_repository import SearchRepository
from endorag_back.services.graph import build_graph_from_settings
from endorag_ingestion.factory import build_storage
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from eval.golden import GoldenItem

logger = logging.getLogger(__name__)

CONCURRENCY = 3  # the free gateway rate-limits bursts
ATTEMPTS = 2  # one retry on an endpoint error


class TurnResult(BaseModel):
    item_id: str
    route: str  # the route the client keeps: emergency, chitchat, …, clarify, refuse
    flags: list[str]
    answer: str
    contexts: list[str]  # texts of the chunks passed to `generate` (empty otherwise)
    doc_ids: list[str]
    seconds: float
    error: str | None = None


def final_route(state: dict) -> str:
    if state["emergency"].emergency:
        return "emergency"
    route = state["route"].route
    if route == "question" and not state["sufficient"]:
        return state["triage"]
    return route


@contextmanager
def profile_graph(profile: str) -> Iterator[CompiledStateGraph]:
    settings = Settings(profile=profile)
    store = build_storage(settings)
    try:
        yield build_graph_from_settings(settings, SearchRepository(store, settings))
    finally:
        store.close()


def _input_state(item: GoldenItem) -> dict:
    past = [
        HumanMessage(m.content) if m.role == "user" else AIMessage(m.content) for m in item.history
    ]
    return {"messages": [*past, HumanMessage(item.user_input)], "query": item.user_input}


async def run_item(graph: CompiledStateGraph, item: GoldenItem) -> TurnResult:
    started = time.perf_counter()
    error = None
    for _ in range(ATTEMPTS):
        try:
            state = await graph.ainvoke(_input_state(item))
            break
        except Exception as exc:  # endpoint errors, timeouts, empty answers
            error = f"{type(exc).__name__}: {exc}"[:200]
            logger.warning("%s failed: %s", item.id, error)
    else:
        return TurnResult(
            item_id=item.id,
            route="error",
            flags=[],
            answer="",
            contexts=[],
            doc_ids=[],
            seconds=time.perf_counter() - started,
            error=error,
        )
    generated = "citations" in state  # only `generate` sets them
    chunks = state.get("chunks", []) if generated else []
    return TurnResult(
        item_id=item.id,
        route=final_route(state),
        flags=state["route"].flags if "route" in state else [],
        answer=state.get("answer", ""),
        contexts=[hit.chunk.text for hit in chunks],
        doc_ids=[hit.chunk.doc_id for hit in chunks],
        seconds=time.perf_counter() - started,
    )


async def run_items(graph: CompiledStateGraph, items: list[GoldenItem]) -> list[TurnResult]:
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def one(item: GoldenItem) -> TurnResult:
        async with semaphore:
            result = await run_item(graph, item)
            logger.info("%s: %s %s (%.1f s)", item.id, result.route, result.flags, result.seconds)
            return result

    return await asyncio.gather(*(one(item) for item in items))
