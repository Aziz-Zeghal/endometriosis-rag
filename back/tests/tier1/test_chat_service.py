"""The chat service: history conversion and the event stream for the API."""

import pytest
from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.services.chat_service import ChatMessage, ChatService
from endorag_back.services.state import RouteEvent, SourcesEvent, TokenEvent
from graph_fakes import STRONG, WEAK, FakeRepository, graph_for, models

QUESTION = '{"route": "question", "asks_for_diagnosis": false, "asks_for_prescription": false}'


def user(text: str) -> ChatMessage:
    return ChatMessage(role="user", content=text)


def assistant(text: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=text)


def service(history_messages: int = 6, profile: str = "patient", repo=None, **small_kw):
    large, small = models(profile, **small_kw)
    graph = graph_for(profile, repo or FakeRepository(STRONG), large, small)
    return ChatService(graph, profile, history_messages), large, small


async def collect(chat: ChatService, messages: list[ChatMessage]) -> list:
    return [event async for event in chat.astream(messages)]


@pytest.mark.asyncio
async def test_streams_route_then_sources_then_tokens():
    chat, large, _ = service(replies={"router": QUESTION})
    large.replies = {"generate": "<think>x</think>L'échographie est l'examen de base [2]."}
    events = await collect(chat, [user("Quel examen en premier ?")])
    assert events[0] == RouteEvent(route="question")
    assert isinstance(events[1], SourcesEvent) and len(events[1].sources) == 2
    tokens = events[2:]
    assert all(isinstance(e, TokenEvent) for e in tokens)
    assert "".join(e.text for e in tokens) == "L'échographie est l'examen de base [2]."


@pytest.mark.asyncio
async def test_router_json_never_reaches_the_stream():
    chat, _, _ = service(replies={"router": '{"route": "chitchat"}'})
    events = await collect(chat, [user("Bonjour")])
    assert events == [
        RouteEvent(route="chitchat"),
        TokenEvent(text=load_prompt("patient", "chitchat")),
    ]


@pytest.mark.asyncio
async def test_keeps_the_latest_message_and_at_most_history_messages_before_it():
    chat, _, small = service(history_messages=2, replies={"router": '{"route": "chitchat"}'})
    await collect(
        chat, [user("un"), assistant("deux"), user("trois"), assistant("quatre"), user("cinq")]
    )
    router_messages = small.messages_of("router")[1:]
    assert [(m.type, m.text) for m in router_messages] == [
        (
            "human",
            "Historique :\nUtilisateur : trois\nAssistant : quatre\n\nDernier message :\ncinq",
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("messages", [[], [user("Bonjour"), assistant("Bonjour !")]])
async def test_the_last_message_must_come_from_the_user(messages):
    chat, _, _ = service()
    with pytest.raises(ValueError, match="last message"):
        await collect(chat, messages)


def text_of(events) -> str:
    return "".join(e.text for e in events if isinstance(e, TokenEvent))


class FailingRepository:
    def retrieve(self, query):
        raise ConnectionError("Qdrant unreachable")


@pytest.mark.asyncio
async def test_generate_failure_ends_with_the_error_message_instead_of_raising():
    chat, large, _ = service(replies={"router": QUESTION})
    large.errors = {"generate"}
    events = await collect(chat, [user("Quel examen en premier ?")])
    assert events[0] == RouteEvent(route="question")
    assert isinstance(events[1], SourcesEvent)
    assert events[2:] == [TokenEvent(text=load_prompt("patient", "error"))]


@pytest.mark.asyncio
async def test_clarify_failure_ends_with_the_error_message():
    chat, large, _ = service(
        repo=FakeRepository(WEAK), replies={"router": QUESTION, "triage": '{"decision": "clarify"}'}
    )
    large.errors = {"clarify"}
    events = await collect(chat, [user("Et ça ?")])
    assert events[-1] == TokenEvent(text=load_prompt("patient", "error"))


@pytest.mark.asyncio
async def test_retrieval_failure_ends_with_the_error_message():
    chat, large, _ = service(repo=FailingRepository(), replies={"router": QUESTION})
    events = await collect(chat, [user("Quel examen en premier ?")])
    assert events == [
        RouteEvent(route="question"),
        TokenEvent(text=load_prompt("patient", "error")),
    ]
    assert large.calls == []


@pytest.mark.asyncio
async def test_an_answer_with_only_reasoning_is_replaced_by_the_error_message():
    chat, large, _ = service(replies={"router": QUESTION})
    large.replies = {"generate": "<think>je réfléchis et je n'ai pas fini"}
    events = await collect(chat, [user("Quel examen en premier ?")])
    assert text_of(events) == load_prompt("patient", "error")


@pytest.mark.asyncio
async def test_safety_model_failure_adds_the_emergency_footer_on_a_gp_red_flag():
    # GP medical red flags are left to the LLM check (no keyword pattern for them).
    chat, large, _ = service(profile="gp", replies={"router": QUESTION}, errors={"safety_gate"})
    large.replies = {"generate": "Réponse [1]."}
    message = "Douleur pelvienne brutale unilatérale et test de grossesse positif, que faire ?"
    events = await collect(chat, [user(message)])
    assert text_of(events) == "Réponse [1].\n\n" + load_prompt("gp", "safety_footer")


@pytest.mark.asyncio
async def test_no_footer_when_the_safety_model_answered():
    chat, large, _ = service(replies={"router": QUESTION})
    large.replies = {"generate": "Réponse [1]."}
    events = await collect(chat, [user("Quel examen en premier ?")])
    assert text_of(events) == "Réponse [1]."


@pytest.mark.asyncio
async def test_logs_the_duration_of_each_node_and_of_the_turn(caplog):
    chat, _, _ = service(replies={"router": '{"route": "chitchat"}'})
    with caplog.at_level("INFO", logger="endorag_back.services.chat_service"):
        await collect(chat, [user("Bonjour")])
    logged = [r.getMessage().split(":")[0] for r in caplog.records]
    assert logged == ["Node safety_gate", "Node router", "Node chitchat", "Turn"]


class FakeStore:
    def search(self, query, k):  # never called: the graph is only built
        raise AssertionError


def test_from_settings_builds_the_graph_of_the_profile():
    settings = Settings(
        _env_file=None,
        profile="gp",
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
    )
    chat = ChatService.from_settings(settings, FakeStore())
    assert set(chat._graph.nodes) >= {"safety_gate", "router", "generate", "refuse"}


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["clarify", "refuse"])
async def test_triage_keeps_the_router_flags_on_the_latest_route(decision):
    # The client replaces `data-route` parts by id: the last one must still carry the flags.
    flagged = '{"route": "question", "asks_for_diagnosis": true, "asks_for_prescription": false}'
    chat, _, _ = service(
        repo=FakeRepository(WEAK),
        replies={"router": flagged, "triage": f'{{"decision": "{decision}"}}'},
    )
    events = await collect(chat, [user("J'ai super mal pendant mes règles, c'est normal ?")])
    routes = [e for e in events if isinstance(e, RouteEvent)]
    assert routes == [
        RouteEvent(route="question", flags=["asks_for_diagnosis"]),
        RouteEvent(route=decision, flags=["asks_for_diagnosis"]),
    ]
