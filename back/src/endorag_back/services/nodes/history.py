"""The conversation as one labelled text, for the nodes that read the past turns."""

from langchain_core.messages import AnyMessage


def transcript(messages: list[AnyMessage]) -> str:
    """The past turns, then the latest message, in one text.

    The router and rewrite send this as a single human message instead of the chat turns:
    in JSON mode the gateway's Nemotron 3 Ultra answered `{"": ""}` to 4 of 6 identical
    multi-turn router calls, and 0 of 6 with the same turns as a transcript.
    """
    *history, last = messages
    text = f"Dernier message :\n{last.text}"
    if history:
        lines = "\n".join(
            f"{'Utilisateur' if m.type == 'human' else 'Assistant'} : {m.text}" for m in history
        )
        text = f"Historique :\n{lines}\n\n{text}"
    return text
