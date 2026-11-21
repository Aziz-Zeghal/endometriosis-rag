"""Fixed answers (emergency, chitchat, out_of_scope, refuse): a prompt file returned verbatim.

No model is called, so these answers cannot contain ungrounded medical text and are instant.
"""

from langgraph.config import get_stream_writer

from endorag_back.services.state import ChatState, TokenEvent


def make_template_node(text: str):
    def template_node(state: ChatState) -> dict:
        get_stream_writer()(TokenEvent(text=text))
        return {"answer": text}

    return template_node
