"""The conversation graph of one profile (composition root).

START → safety_gate → emergency | router
router → chitchat | out_of_scope | rewrite → retrieve → generate | triage
triage → clarify | refuse
emergency, chitchat, out_of_scope, generate, clarify, refuse → END
"""

from typing import Literal

from endorag_ingestion.core.settings import Profile
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from endorag_back.config.settings import Settings
from endorag_back.prompts import load_prompt
from endorag_back.repositories.search_repository import SearchRepository
from endorag_back.services.llm import chat_model
from endorag_back.services.nodes.clarify import make_clarify_node
from endorag_back.services.nodes.generate import make_generate_node
from endorag_back.services.nodes.retrieve import make_retrieve_node
from endorag_back.services.nodes.rewrite import make_rewrite_node
from endorag_back.services.nodes.router import make_router_node
from endorag_back.services.nodes.safety_gate import make_safety_gate_node
from endorag_back.services.nodes.template import make_template_node
from endorag_back.services.nodes.triage import make_triage_node
from endorag_back.services.safety import (
    CompositeSafetyCheck,
    KeywordSafetyCheck,
    LlmSafetyCheck,
    SafetyCheck,
)
from endorag_back.services.state import ChatState


def _after_safety(state: ChatState) -> Literal["emergency", "router"]:
    return "emergency" if state["emergency"].emergency else "router"


def _after_router(state: ChatState) -> Literal["chitchat", "out_of_scope", "rewrite"]:
    route = state["route"].route
    return "rewrite" if route == "question" else route


def _after_retrieve(state: ChatState) -> Literal["generate", "triage"]:
    return "generate" if state["sufficient"] else "triage"


def _after_triage(state: ChatState) -> Literal["clarify", "refuse"]:
    return state["triage"]


def build_safety_check(settings: Settings, profile: Profile, small: BaseChatModel) -> SafetyCheck:
    """Keyword patterns first, then the small model unless `SAFETY_LLM_ENABLED` is off."""
    checks: list[SafetyCheck] = [KeywordSafetyCheck(profile)]
    if settings.safety_llm_enabled:
        prompt = load_prompt(profile, "safety_gate")
        checks.append(LlmSafetyCheck(small, prompt, settings.safety_timeout_s))
    return CompositeSafetyCheck(checks)


def build_graph(
    profile: Profile,
    safety: SafetyCheck,
    repo: SearchRepository,
    large: BaseChatModel,
    small: BaseChatModel,
) -> CompiledStateGraph:
    """`large` answers (generate, clarify); `small` classifies and rewrites (router, rewrite,
    triage). Template nodes return their prompt file verbatim."""

    def prompt(node: str) -> str:
        return load_prompt(profile, node)

    graph = StateGraph(ChatState)
    graph.add_node("safety_gate", make_safety_gate_node(safety))
    graph.add_node("emergency", make_template_node(prompt("emergency")))
    graph.add_node("router", make_router_node(small, prompt("router")))
    graph.add_node("chitchat", make_template_node(prompt("chitchat")))
    graph.add_node("out_of_scope", make_template_node(prompt("out_of_scope")))
    graph.add_node("rewrite", make_rewrite_node(small, prompt("rewrite")))
    graph.add_node("retrieve", make_retrieve_node(repo))
    graph.add_node("generate", make_generate_node(large, prompt("generate")))
    graph.add_node("triage", make_triage_node(small, prompt("triage")))
    graph.add_node("clarify", make_clarify_node(large, prompt("clarify")))
    graph.add_node("refuse", make_template_node(prompt("refuse")))

    graph.add_edge(START, "safety_gate")
    graph.add_conditional_edges("safety_gate", _after_safety)
    graph.add_conditional_edges("router", _after_router)
    graph.add_edge("rewrite", "retrieve")
    graph.add_conditional_edges("retrieve", _after_retrieve)
    graph.add_conditional_edges("triage", _after_triage)
    for node in ("emergency", "chitchat", "out_of_scope", "generate", "clarify", "refuse"):
        graph.add_edge(node, END)
    return graph.compile()


def build_graph_from_settings(settings: Settings, repo: SearchRepository) -> CompiledStateGraph:
    """The graph of `settings.profile` with the configured chat models."""
    small = chat_model(settings, "small", temperature=0)  # same message, same route
    large = chat_model(
        settings, "large", temperature=settings.temperature, max_tokens=settings.max_tokens
    )
    safety = build_safety_check(settings, settings.profile, small)
    return build_graph(settings.profile, safety, repo, large, small)
