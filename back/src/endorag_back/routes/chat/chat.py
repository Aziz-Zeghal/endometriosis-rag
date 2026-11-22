"""POST /api/chat: the conversation graph streamed in the AI SDK UI message stream format.

Request: the body the AI SDK chat transport sends (`messages` with `parts`). Response:
server-sent events, one JSON part per `data:` line, in this order:
`start`, `data-route` (one per route decision), one `source-url` per source then a
`data-sources` part for the widget's source cards, `text-start`, `text-delta`…, `text-end`,
`finish`, then `[DONE]`. See https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol.

One app serves both profiles: the body's `profile` (default `PROFILE`) picks the graph.
"""

import json
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Literal
from uuid import uuid4

from endorag_ingestion.core.settings import Profile
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from endorag_back.prompts import load_prompt
from endorag_back.services.chat_service import ChatMessage, ChatService
from endorag_back.services.state import ChatEvent, RouteEvent, SourcesEvent, TokenEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class UIMessagePart(BaseModel):
    type: str  # only "text" parts are read; source and data parts sent back are ignored
    text: str = ""


class UIMessage(BaseModel):
    id: str = ""
    role: Literal["system", "user", "assistant"]
    parts: list[UIMessagePart]


class ChatRequest(BaseModel):
    id: str = ""
    messages: list[UIMessage] = Field(min_length=1)
    profile: Profile | None = None  # graph to answer with; the server's `PROFILE` when absent


class SourceCard(BaseModel):
    """One item of the `data-sources` part: `id` is the number cited in the answer ([1]…)."""

    id: int
    title: str
    source: str  # publishing organisation
    date: date
    url: str  # with `#page=N` for PDF chunks
    page: int | None = None


def get_chat_services(request: Request) -> dict[Profile, ChatService]:
    """One chat service per profile, built at startup."""
    return request.app.state.chat_services


def to_chat_messages(messages: list[UIMessage]) -> list[ChatMessage]:
    """User and assistant text; system messages and messages without text are dropped."""
    converted = []
    for message in messages:
        text = "".join(p.text for p in message.parts if p.type == "text").strip()
        if message.role != "system" and text:
            converted.append(ChatMessage(role=message.role, content=text))
    return converted


def _sse(part: dict | str) -> str:
    payload = part if isinstance(part, str) else json.dumps(part, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def ui_message_stream(events: AsyncIterator[ChatEvent], error_message: str):
    """Turn chat events into UI message stream parts; an exception ends the text politely."""
    yield _sse({"type": "start", "messageId": f"msg-{uuid4().hex}"})
    text_id = f"text-{uuid4().hex}"
    text_started = False
    try:
        async for event in events:
            if isinstance(event, RouteEvent):
                # Same id: the client keeps the latest route (question, then clarify).
                yield _sse({"type": "data-route", "id": "route", "data": event.model_dump()})
            elif isinstance(event, SourcesEvent):
                for c in event.sources:
                    part = {"type": "source-url", "sourceId": str(c.index), "url": c.url}
                    yield _sse(part | {"title": c.title})
                cards = [
                    SourceCard(
                        id=c.index,
                        title=c.title,
                        source=c.source,
                        date=c.published,
                        url=c.url,
                        page=c.page,
                    ).model_dump(mode="json")
                    for c in event.sources
                ]
                yield _sse({"type": "data-sources", "id": "sources", "data": cards})
            elif isinstance(event, TokenEvent) and event.text:
                if not text_started:
                    text_started = True
                    yield _sse({"type": "text-start", "id": text_id})
                yield _sse({"type": "text-delta", "id": text_id, "delta": event.text})
    except Exception:
        logger.exception("Chat stream failed")
        if not text_started:
            yield _sse({"type": "text-start", "id": text_id})
        delta = ("\n\n" if text_started else "") + error_message
        yield _sse({"type": "text-delta", "id": text_id, "delta": delta})
        text_started = True
    if text_started:
        yield _sse({"type": "text-end", "id": text_id})
    yield _sse({"type": "finish"})
    yield _sse("[DONE]")


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    services: Annotated[dict[Profile, ChatService], Depends(get_chat_services)],
) -> StreamingResponse:
    profile = body.profile or request.app.state.settings.profile
    messages = to_chat_messages(body.messages)
    if not messages or messages[-1].role != "user":
        raise HTTPException(422, "The last message must be a user message with text")
    return StreamingResponse(
        ui_message_stream(services[profile].astream(messages), load_prompt(profile, "error")),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # no proxy buffering, tokens arrive as they are written
        },
    )
