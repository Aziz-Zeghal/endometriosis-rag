"""Retrieve: the search repository's chunks and evidence verdict for the standalone query."""

from endorag_back.repositories.search_repository import SearchRepository
from endorag_back.services.state import ChatState


def make_retrieve_node(repo: SearchRepository):
    # Synchronous (embedding call + local Qdrant): LangGraph runs it in a worker thread.
    def retrieve_node(state: ChatState) -> dict:
        retrieval = repo.retrieve(state["search_query"])
        return {"chunks": retrieval.chunks, "sufficient": retrieval.sufficient}

    return retrieve_node
