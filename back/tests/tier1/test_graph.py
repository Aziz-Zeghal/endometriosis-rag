"""The conversation graph with scripted chat models and a fake repository.

Every route is reachable, the storyline of docs/scenario.md routes as specified, and the
nodes degrade safely when a model fails or replies badly. Generated text is never judged.
"""

import pytest
from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.services import graph as graph_module
from endorag_back.services.nodes.generate import DIAGNOSIS_MARKER, PRESCRIPTION_MARKER
from endorag_back.services.state import RouteDecision, RouteEvent, SourcesEvent, TokenEvent
from graph_fakes import STRONG, WEAK, FakeRepository, conversation, graph_for, models, run
from langchain_core.messages import HumanMessage, SystemMessage

QUESTION = '{"route": "question", "asks_for_diagnosis": false, "asks_for_prescription": false}'
DIAGNOSIS = '{"route": "question", "asks_for_diagnosis": true, "asks_for_prescription": false}'
PRESCRIPTION = '{"route": "question", "asks_for_diagnosis": false, "asks_for_prescription": true}'
TO_GENERATE = ["safety_gate", "router", "rewrite", "retrieve", "generate"]


def answer_text(events) -> str:
    return "".join(e.text for e in events if isinstance(e, TokenEvent))


# Every route


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["patient", "gp"])
@pytest.mark.parametrize(
    ("message", "router", "retrieval", "triage", "path"),
    [
        ("J'ai envie de mourir.", None, STRONG, None, ["safety_gate", "emergency"]),
        ("Bonjour !", '{"route": "chitchat"}', STRONG, None, ["safety_gate", "router", "chitchat"]),
        (
            "Une recette de crêpes ?",
            '{"route": "out_of_scope"}',
            STRONG,
            None,
            ["safety_gate", "router", "out_of_scope"],
        ),
        ("Question couverte", QUESTION, STRONG, None, TO_GENERATE),
        (
            "Et ça ?",
            QUESTION,
            WEAK,
            '{"decision": "clarify"}',
            ["safety_gate", "router", "rewrite", "retrieve", "triage", "clarify"],
        ),
        (
            "Question absente des sources",
            QUESTION,
            WEAK,
            '{"decision": "refuse"}',
            ["safety_gate", "router", "rewrite", "retrieve", "triage", "refuse"],
        ),
    ],
)
async def test_every_route_is_reachable(profile, message, router, retrieval, triage, path):
    large, small = models(profile, replies={"router": router or "", "triage": triage or ""})
    graph = graph_for(profile, FakeRepository(retrieval), large, small)
    nodes, events, state = await run(graph, conversation(message))
    assert nodes == path
    assert state["answer"]
    assert answer_text(events) == state["answer"]


@pytest.mark.asyncio
@pytest.mark.parametrize("node", ["emergency", "chitchat", "out_of_scope", "refuse"])
async def test_template_nodes_return_their_prompt_verbatim(node):
    route = node if node in ("chitchat", "out_of_scope") else "question"
    replies = {
        "router": f'{{"route": "{route}"}}',
        "triage": '{"decision": "refuse"}',
    }
    message = "Je veux mourir." if node == "emergency" else "Message"
    large, small = models("patient", replies=replies)
    graph = graph_for("patient", FakeRepository(WEAK), large, small)
    _, events, state = await run(graph, conversation(message))
    assert state["answer"] == load_prompt("patient", node)
    assert large.calls == []  # never the large model
    assert not any(isinstance(e, SourcesEvent) for e in events)


# Storyline (docs/scenario.md)

TURN_1 = (
    "J'ai super mal au ventre pendant mes règles, au point de rater les cours, et le Doliprane "
    "me fait rien. C'est normal ?"
)
TURN_2 = "Et je dois aller voir qui ? Ma généraliste ou direct un gynéco ?"
TURN_3 = (
    "On m'a dit qu'il faut se faire opérer pour savoir. Et mon écho était normale, donc j'ai rien ?"
)
TURN_4 = (
    "Franchement dis-moi juste si j'ai une endométriose. Pose-moi des questions et donne-moi un "
    "score."
)
TURN_5 = "Le test salivaire de TikTok, je peux l'acheter en pharmacie ?"
TURN_6 = (
    "Je suis diagnostiquée et je rate souvent le boulot. J'ai droit au 100 % ? Et la RQTH, ça "
    "sert à quoi ?"
)
TURN_7 = "Les culottes menstruelles sont remboursées depuis octobre, c'est vrai ?"
TURN_8 = (
    "Ça fait trois jours que j'ai une douleur horrible, rien ne marche, je vomis, et honnêtement "
    "j'ai envie que tout s'arrête."
)
TURN_9 = (
    "Quels signes d'appel doivent faire évoquer une endométriose, et quelle imagerie en première "
    "intention ?"
)
TURN_10 = "Ma patiente a 24 ans, je lui prescris quoi ?"
ANSWER = "Réponse de l'assistant [1]."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("profile", "history", "message", "router", "flag"),
    [
        ("patient", [], TURN_1, DIAGNOSIS, DIAGNOSIS_MARKER),
        ("patient", [TURN_1, ANSWER], TURN_2, QUESTION, None),
        ("patient", [TURN_1, ANSWER, TURN_2, ANSWER], TURN_3, DIAGNOSIS, DIAGNOSIS_MARKER),
        ("patient", [TURN_2, ANSWER, TURN_3, ANSWER], TURN_4, DIAGNOSIS, DIAGNOSIS_MARKER),
        ("patient", [TURN_3, ANSWER, TURN_4, ANSWER], TURN_5, QUESTION, None),
        ("patient", [], TURN_6, QUESTION, None),
        ("gp", [], TURN_9, QUESTION, None),
        ("gp", [TURN_9, ANSWER], TURN_10, PRESCRIPTION, PRESCRIPTION_MARKER),
    ],
    ids=["turn1", "turn2", "turn3", "turn4", "turn5", "turn6", "turn9", "turn10"],
)
async def test_storyline_answered_turns(profile, history, message, router, flag):
    standalone = "Requête autonome reformulée"
    large, small = models(profile, replies={"router": router, "rewrite": standalone})
    repo = FakeRepository(STRONG)
    nodes, events, _ = await run(
        graph_for(profile, repo, large, small), conversation(*history, message)
    )

    assert nodes == TO_GENERATE
    # Follow-ups are rewritten from the history; a first message is searched as typed.
    assert repo.queries == [standalone if history else message]
    assert ("rewrite" in small.nodes_called()) == bool(history)
    assert large.nodes_called() == ["generate"]
    prompt = large.messages_of("generate")[-1].text
    for marker in (DIAGNOSIS_MARKER, PRESCRIPTION_MARKER):
        assert (marker in prompt) == (marker == flag)
    # Route first, then the sources, then the answer tokens.
    flags = {
        DIAGNOSIS_MARKER: ["asks_for_diagnosis"],
        PRESCRIPTION_MARKER: ["asks_for_prescription"],
    }
    assert events[0] == RouteEvent(route="question", flags=flags.get(flag, []))
    assert isinstance(events[1], SourcesEvent)
    assert all(isinstance(e, TokenEvent) for e in events[2:])


def test_storyline_turn_4_prompt_forbids_a_diagnosis_and_points_to_a_professional():
    system = load_prompt("patient", "generate")
    assert DIAGNOSIS_MARKER in system
    assert "Ne dis jamais à l'utilisatrice qu'elle a ou qu'elle n'a pas une endométriose" in system
    assert "à qui s'adresser" in system


def test_storyline_turns_5_and_6_prompt_warns_on_freshness_and_promises_no_eligibility():
    system = load_prompt("patient", "generate")
    assert "a pu changer : vérifiez-la sur" in system  # turn 5: the freshness sentence
    assert "au cas par cas" in system and "Ne dis jamais que l'utilisatrice a droit" in system


def test_storyline_turn_10_gp_prompt_refuses_individual_prescription():
    system = load_prompt("gp", "generate")
    assert PRESCRIPTION_MARKER in system
    assert "Pas de prescription individuelle" in system
    router = load_prompt("gp", "router")
    assert "je lui prescris quoi" in router  # the example the router flags


@pytest.mark.asyncio
async def test_storyline_turn_7_not_in_corpus_is_refused_without_the_large_model():
    large, small = models(
        "patient", replies={"router": QUESTION, "triage": '{"decision": "refuse"}'}
    )
    nodes, events, state = await run(
        graph_for("patient", FakeRepository(WEAK), large, small), conversation(TURN_7)
    )
    assert nodes == ["safety_gate", "router", "rewrite", "retrieve", "triage", "refuse"]
    assert state["answer"] == load_prompt("patient", "refuse")
    assert large.calls == []
    assert RouteEvent(route="refuse") in events
    assert not any(isinstance(e, SourcesEvent) for e in events)


@pytest.mark.asyncio
async def test_storyline_turn_8_emergency_calls_no_model_and_no_retrieval():
    large, small = models("patient")
    repo = FakeRepository(STRONG)
    history = [TURN_6, ANSWER, TURN_7, load_prompt("patient", "refuse")]
    nodes, events, state = await run(
        graph_for("patient", repo, large, small), conversation(*history, TURN_8)
    )
    assert nodes == ["safety_gate", "emergency"]
    assert events == [RouteEvent(route="emergency"), TokenEvent(text=state["answer"])]
    assert state["answer"] == load_prompt("patient", "emergency")
    assert repo.queries == [] and large.calls == [] and small.calls == []


# Failures and parsing


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "small_kw",
    [
        {"replies": {"router": "Ce n'est pas du JSON."}},
        {"replies": {"router": '{"route": "météo"}'}},
        {"errors": {"router"}},
    ],
    ids=["not-json", "unknown-route", "endpoint-error"],
)
async def test_router_failure_falls_back_to_question(small_kw):
    large, small = models("patient", **small_kw)
    nodes, _, state = await run(
        graph_for("patient", FakeRepository(STRONG), large, small), conversation("Bonjour")
    )
    assert nodes == TO_GENERATE
    assert state["route"] == RouteDecision(route="question")


@pytest.mark.asyncio
async def test_router_reads_json_after_inline_reasoning_and_sees_the_history():
    large, small = models(
        "patient", replies={"router": '<think>salutation</think>{"route": "chitchat"}'}
    )
    graph = graph_for("patient", FakeRepository(STRONG), large, small)
    nodes, _, _ = await run(graph, conversation("Bonjour", "Bonjour !", "Merci beaucoup"))
    assert nodes == ["safety_gate", "router", "chitchat"]
    # One labelled transcript: in JSON mode, chat turns gave malformed replies (D-25).
    assert [m.text for m in small.messages_of("router")[1:]] == [
        "Historique :\nUtilisateur : Bonjour\nAssistant : Bonjour !\n\n"
        "Dernier message :\nMerci beaucoup"
    ]


@pytest.mark.asyncio
async def test_safety_model_failure_never_blocks_the_keyword_gate():
    large, small = models("patient", errors={"safety_gate"})
    nodes, _, _ = await run(
        graph_for("patient", FakeRepository(STRONG), large, small),
        conversation("J'ai une douleur brutale à droite."),
    )
    assert nodes == ["safety_gate", "emergency"]
    assert small.calls == []  # the keyword hit short-circuits the model


@pytest.mark.asyncio
async def test_safety_model_failure_lets_a_normal_question_through():
    large, small = models("patient", errors={"safety_gate"}, replies={"router": QUESTION})
    nodes, _, state = await run(
        graph_for("patient", FakeRepository(STRONG), large, small), conversation(TURN_5)
    )
    assert nodes == TO_GENERATE
    assert state["emergency"].source == "llm-error"


@pytest.mark.asyncio
async def test_safety_model_can_trigger_the_emergency():
    large, small = models(
        "patient", replies={"safety_gate": '{"emergency": true, "kind": "psychological"}'}
    )
    nodes, _, _ = await run(
        graph_for("patient", FakeRepository(STRONG), large, small),
        conversation("Je ne vois plus l'intérêt de continuer."),
    )
    assert nodes == ["safety_gate", "emergency"]


@pytest.mark.asyncio
@pytest.mark.parametrize("small_kw", [{"replies": {"rewrite": ""}}, {"errors": {"rewrite"}}])
async def test_rewrite_failure_searches_the_raw_message(small_kw):
    small_kw["replies"] = {**small_kw.get("replies", {}), "router": QUESTION}
    large, small = models("patient", **small_kw)
    repo = FakeRepository(STRONG)
    await run(graph_for("patient", repo, large, small), conversation(TURN_1, ANSWER, TURN_2))
    assert repo.queries == [TURN_2]


@pytest.mark.asyncio
async def test_rewrite_sees_the_history_and_strips_reasoning():
    large, small = models(
        "patient", replies={"router": QUESTION, "rewrite": "<think>…</think>Quel médecin ?"}
    )
    repo = FakeRepository(STRONG)
    await run(graph_for("patient", repo, large, small), conversation(TURN_1, ANSWER, TURN_2))
    assert repo.queries == ["Quel médecin ?"]
    human = small.messages_of("rewrite")[-1].text
    assert TURN_1 in human and ANSWER in human and human.endswith(TURN_2)


@pytest.mark.asyncio
@pytest.mark.parametrize("small_kw", [{"replies": {"triage": "oui"}}, {"errors": {"triage"}}])
async def test_triage_failure_refuses(small_kw):
    small_kw["replies"] = {**small_kw.get("replies", {}), "router": QUESTION}
    large, small = models("patient", **small_kw)
    nodes, _, _ = await run(
        graph_for("patient", FakeRepository(WEAK), large, small), conversation(TURN_7)
    )
    assert nodes[-1] == "refuse"


# Generation


@pytest.mark.asyncio
async def test_generate_prompt_has_numbered_dated_passages_and_the_citation_rule():
    large, small = models("patient", replies={"router": QUESTION})
    _, events, state = await run(
        graph_for("patient", FakeRepository(STRONG), large, small), conversation(TURN_5)
    )
    system, human = (m.text for m in large.messages_of("generate"))
    assert "[1]" in system and "plus récent" in system  # citation and recency rules
    assert human.startswith("Passages :")
    assert "[1] Organisme, « Titre recent », 2025-01-01\n" in human
    assert "[2] Organisme, « Titre guide », 2017-12-01, page 4\n" in human
    assert STRONG.chunks[1].chunk.text in human
    assert human.index("[1]") < human.index("[2]") < human.index(TURN_5)

    sources = next(e for e in events if isinstance(e, SourcesEvent)).sources
    assert [c.index for c in sources] == [1, 2]
    assert sources[1].url == "https://example.org/guide.pdf#page=4"  # page link
    assert state["citations"] == sources


@pytest.mark.asyncio
async def test_generate_streams_without_inline_reasoning():
    large, small = models("patient", replies={"router": QUESTION})
    large.replies = {"generate": "<think>je réfléchis longuement</think>\n\nRéponse [1]."}
    large.piece_size = 3  # tags split across chunks
    _, events, state = await run(
        graph_for("patient", FakeRepository(STRONG), large, small), conversation(TURN_5)
    )
    assert answer_text(events) == "Réponse [1]."
    assert state["answer"] == "Réponse [1]."


@pytest.mark.asyncio
async def test_clarify_streams_one_question_from_the_conversation():
    large, small = models(
        "patient", replies={"router": QUESTION, "triage": '{"decision": "clarify"}'}
    )
    large.replies = {"clarify": "De quel examen parlez-vous ?"}
    _, events, state = await run(
        graph_for("patient", FakeRepository(WEAK), large, small),
        conversation("J'ai fait des examens.", "Lesquels ?", "Et ça ?"),
    )
    assert large.nodes_called() == ["clarify"]
    assert answer_text(events) == state["answer"] == "De quel examen parlez-vous ?"
    assert events[:2] == [RouteEvent(route="question"), RouteEvent(route="clarify")]
    # One labelled transcript, not chat turns (D-29).
    system, human = large.messages_of("clarify")
    assert isinstance(system, SystemMessage) and isinstance(human, HumanMessage)
    assert "Historique :" in human.text and "Dernier message :\nEt ça ?" in human.text


@pytest.mark.asyncio
async def test_generate_stores_exactly_what_it_streamed_when_the_opening_tag_is_missing():
    large, small = models("patient", replies={"router": QUESTION})
    large.replies = {"generate": "raisonnement caché</think>Réponse [1]."}
    large.piece_size = 4
    _, events, state = await run(
        graph_for("patient", FakeRepository(STRONG), large, small), conversation(TURN_5)
    )
    assert "</think>" not in answer_text(events)
    assert answer_text(events) == state["answer"]


def test_classification_and_rewrite_model_runs_at_temperature_zero(monkeypatch):
    real_chat_model = graph_module.chat_model
    options: dict[str, dict] = {}

    def recording_chat_model(settings, size, **kwargs):
        options[size] = kwargs
        return real_chat_model(settings, size, **kwargs)

    monkeypatch.setattr(graph_module, "chat_model", recording_chat_model)
    settings = Settings(
        _env_file=None,
        llm_base_url="http://llm.test/v1",
        llm_api_key="secret",
        llm_model="large-model",
        llm_small_model="small-model",
    )
    graph_module.build_graph_from_settings(settings, FakeRepository(STRONG))
    assert options["small"]["temperature"] == 0  # the same message always takes the same route
    assert options["large"]["temperature"] == settings.temperature
