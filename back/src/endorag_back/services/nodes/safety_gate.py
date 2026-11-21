"""Safety gate: runs before anything else, on the latest user message."""

import logging

from langgraph.config import get_stream_writer

from endorag_back.services.safety import SafetyCheck
from endorag_back.services.state import ChatState, RouteEvent

logger = logging.getLogger(__name__)


def make_safety_gate_node(safety: SafetyCheck):
    async def safety_gate_node(state: ChatState) -> dict:
        # The checks never raise: a failing LLM check returns source="llm-error".
        decision = await safety.check(state["query"])
        logger.info("Safety gate: emergency=%s source=%s", decision.emergency, decision.source)
        if decision.emergency:
            get_stream_writer()(RouteEvent(route="emergency"))
        return {"emergency": decision}

    return safety_gate_node
