"""The real app (both profiles) per test module, with the module's `PROFILE` as default and
in every request; the app, and so the local Qdrant lock, lives for the module."""

import pytest
from endorag_back.config.settings import Settings
from endorag_back.routes.entrypoint import create_app
from fastapi.testclient import TestClient
from storyline import Conversation


@pytest.fixture(scope="module")
def client(request):
    with TestClient(create_app(Settings(profile=request.module.PROFILE))) as client:
        yield client


@pytest.fixture(scope="module")
def new_conversation(client, request):
    return lambda: Conversation(client, request.module.PROFILE)
