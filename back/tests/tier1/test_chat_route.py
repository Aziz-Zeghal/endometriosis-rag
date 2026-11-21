"""POST /api/chat: request conversion and the AI SDK UI message stream."""

import json
from datetime import date

import pytest
from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.routes import entrypoint
from endorag_back.routes.chat.chat import get_chat_service
from endorag_back.services.chat_service import ChatMessage, ChatService
from endorag_back.services.state import Citation, RouteEvent, SourcesEvent, TokenEvent
from fastapi.testclient import TestClient
from graph_fakes import STRONG, FakeRepository, graph_for, models

CITATIONS = [
    Citation(
        index=1,
        doc_id="recent",
        title="Titre recent",
        source="Organisme",
        url="https://example.org/recent",
        published=date(2025, 1, 1),
    ),
    Citation(
        index=2,
        doc_id="guide",
        title="Titre guide",
        source="HAS",
        url="https://example.org/guide.pdf#page=4",
        published=date(2017, 12, 1),
        page=4,
    ),
]


class FakeStore:
    collection = "patient__test"

    def count(self) -> int:
        return 0

    def close(self) -> None:
        pass


class FakeChatService:
    def __init__(self, events: list, fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.messages: list[ChatMessage] = []

    async def astream(self, messages: list[ChatMessage]):
        self.messages = messages
        for event in self.events:
            yield event
        if self.fail:
            raise RuntimeError("secret internal detail")


@pytest.fixture
def client_for(monkeypatch):
    monkeypatch.setattr(entrypoint, "build_storage", lambda s: FakeStore())
    clients = []

    def make(service) -> TestClient:
        app = entrypoint.create_app(
            Settings(
                _env_file=None,
                profile="patient",
                llm_base_url="http://llm.test/v1",
                llm_api_key="secret",
                llm_model="large-model",
                llm_small_model="small-model",
                cors_origins=["https://host.test"],
            )
        )
        app.dependency_overrides[get_chat_service] = lambda: service
        clients.append(TestClient(app).__enter__())
        return clients[-1]

    yield make
    for client in clients:
        client.__exit__(None, None, None)


def body(*texts: str, **extra) -> dict:
    """AI SDK transport body from alternating user / assistant texts, the last from the user."""
    roles = ["user", "assistant"] if len(texts) % 2 else ["assistant", "user"]
    messages = [
        {"id": f"m{i}", "role": roles[i % 2], "parts": [{"type": "text", "text": t}]}
        for i, t in enumerate(texts)
    ]
    return {"id": "chat-1", "messages": messages} | extra


def parts(response) -> list:
    """The `data:` payloads, JSON-decoded except the final `[DONE]`."""
    lines = [line for line in response.text.split("\n\n") if line]
    assert all(line.startswith("data: ") for line in lines)
    return [p if p == "[DONE]" else json.loads(p) for p in (x[6:] for x in lines)]


def test_streams_the_exact_part_sequence(client_for):
    service = FakeChatService(
        [
            RouteEvent(route="question", flags=["asks_for_diagnosis"]),
            SourcesEvent(sources=CITATIONS),
            TokenEvent(text="L'échographie "),
            TokenEvent(text="est l'examen de base [2]."),
        ]
    )
    response = client_for(service).post("/api/chat", json=body("Quel examen ?"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"

    got = parts(response)
    message_id, text_id = got[0]["messageId"], got[5]["id"]
    assert got == [
        {"type": "start", "messageId": message_id},
        {
            "type": "data-route",
            "id": "route",
            "data": {"type": "route", "route": "question", "flags": ["asks_for_diagnosis"]},
        },
        {
            "type": "source-url",
            "sourceId": "1",
            "url": "https://example.org/recent",
            "title": "Titre recent",
        },
        {
            "type": "source-url",
            "sourceId": "2",
            "url": "https://example.org/guide.pdf#page=4",
            "title": "Titre guide",
        },
        {
            "type": "data-sources",
            "id": "sources",
            "data": [
                {
                    "id": 1,
                    "title": "Titre recent",
                    "source": "Organisme",
                    "date": "2025-01-01",
                    "url": "https://example.org/recent",
                    "page": None,
                },
                {
                    "id": 2,
                    "title": "Titre guide",
                    "source": "HAS",
                    "date": "2017-12-01",
                    "url": "https://example.org/guide.pdf#page=4",
                    "page": 4,
                },
            ],
        },
        {"type": "text-start", "id": text_id},
        {"type": "text-delta", "id": text_id, "delta": "L'échographie "},
        {"type": "text-delta", "id": text_id, "delta": "est l'examen de base [2]."},
        {"type": "text-end", "id": text_id},
        {"type": "finish"},
        "[DONE]",
    ]
    assert message_id and text_id


def test_converts_the_transport_body_to_chat_messages(client_for):
    service = FakeChatService([TokenEvent(text="ok")])
    request = body("Bonjour", "Bonjour !", "Et pour la fertilité ?")
    request["messages"].insert(0, {"role": "system", "parts": [{"type": "text", "text": "x"}]})
    request["messages"][2]["parts"] += [
        {"type": "source-url", "sourceId": "1", "url": "https://example.org"},
        {"type": "data-route", "data": {"route": "chitchat"}},
    ]
    request["messages"][3]["parts"] = [
        {"type": "step-start"},
        {"type": "text", "text": "Et pour "},
        {"type": "text", "text": "la fertilité ?"},
    ]
    assert client_for(service).post("/api/chat", json=request).status_code == 200
    assert service.messages == [
        ChatMessage(role="user", content="Bonjour"),
        ChatMessage(role="assistant", content="Bonjour !"),
        ChatMessage(role="user", content="Et pour la fertilité ?"),
    ]


@pytest.mark.parametrize(
    "request_body",
    [
        {"messages": [{"role": "assistant", "parts": [{"type": "text", "text": "Bonjour !"}]}]},
        {"messages": [{"role": "user", "parts": [{"type": "file"}]}]},  # no text
        {"messages": []},
    ],
)
def test_rejects_a_request_without_a_final_user_text(client_for, request_body):
    service = FakeChatService([])
    assert client_for(service).post("/api/chat", json=request_body).status_code == 422


def test_profile_from_the_request_must_match_the_server(client_for):
    client = client_for(FakeChatService([TokenEvent(text="ok")]))
    assert client.post("/api/chat", json=body("Bonjour", profile="patient")).status_code == 200
    assert client.post("/api/chat", json=body("Bonjour", profile="gp")).status_code == 400


def text_of(got: list) -> str:
    return "".join(p["delta"] for p in got if isinstance(p, dict) and p["type"] == "text-delta")


def test_an_error_mid_stream_ends_the_message_with_the_fixed_text(client_for):
    service = FakeChatService([RouteEvent(route="question"), TokenEvent(text="Début")], fail=True)
    response = client_for(service).post("/api/chat", json=body("Quel examen ?"))
    got = parts(response)
    assert text_of(got) == "Début\n\n" + load_prompt("patient", "error")
    assert [p if p == "[DONE]" else p["type"] for p in got[-3:]] == ["text-end", "finish", "[DONE]"]
    assert "secret internal detail" not in response.text and "Traceback" not in response.text


def test_an_error_before_any_text_still_opens_and_closes_the_text(client_for):
    response = client_for(FakeChatService([], fail=True)).post("/api/chat", json=body("Salut"))
    types = [p if p == "[DONE]" else p["type"] for p in parts(response)]
    assert types == ["start", "text-start", "text-delta", "text-end", "finish", "[DONE]"]
    assert text_of(parts(response)) == load_prompt("patient", "error")


def test_emergency_streams_the_fixed_message_without_sources(client_for):
    # The real chat service and graph: the keyword check answers, no model is called.
    large, small = models("patient")
    repo = FakeRepository(STRONG)
    service = ChatService(graph_for("patient", repo, large, small), "patient", 6)
    message = "honnêtement j'ai envie que tout s'arrête"
    got = parts(client_for(service).post("/api/chat", json=body(message)))
    assert got[1]["type"] == "data-route" and got[1]["data"]["route"] == "emergency"
    assert not any(isinstance(p, dict) and p["type"].startswith("source") for p in got)
    assert not any(isinstance(p, dict) and p["type"] == "data-sources" for p in got)
    assert text_of(got) == load_prompt("patient", "emergency")
    assert repo.queries == [] and small.calls == [] and large.calls == []


def test_route_flags_and_sources_come_from_the_graph_before_the_text(client_for):
    large, small = models(
        "patient",
        replies={
            "router": '{"route": "question", "asks_for_diagnosis": true, '
            '"asks_for_prescription": false}'
        },
    )
    large.replies = {"generate": "Une douleur qui gêne la vie quotidienne fait consulter [1]."}
    service = ChatService(graph_for("patient", FakeRepository(STRONG), large, small), "patient", 6)
    got = parts(client_for(service).post("/api/chat", json=body("C'est normal ?")))
    types = [p if p == "[DONE]" else p["type"] for p in got]
    assert types[:5] == ["start", "data-route", "source-url", "source-url", "data-sources"]
    assert types.index("data-sources") < types.index("text-start")
    assert got[1]["data"]["flags"] == ["asks_for_diagnosis"]
    assert got[3]["url"].endswith(".pdf#page=4")
    assert text_of(got) == "Une douleur qui gêne la vie quotidienne fait consulter [1]."


def test_cors_allows_the_widget_origin_on_chat(client_for):
    client = client_for(FakeChatService([TokenEvent(text="ok")]))
    preflight = client.options(
        "/api/chat",
        headers={
            "Origin": "https://host.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://host.test"
    response = client.post(
        "/api/chat", json=body("Bonjour"), headers={"Origin": "https://host.test"}
    )
    assert response.headers["access-control-allow-origin"] == "https://host.test"
    other = client.post("/api/chat", json=body("Bonjour"), headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in other.headers
