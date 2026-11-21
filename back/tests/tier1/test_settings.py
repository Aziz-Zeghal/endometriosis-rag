import pytest
from endorag_back.config.settings import Settings
from pydantic import ValidationError

REQUIRED = {
    "LLM_BASE_URL": "http://llm.test/v1",
    "LLM_API_KEY": "secret",
    "LLM_MODEL": "large-model",
    "LLM_SMALL_MODEL": "small-model",
}


@pytest.fixture
def env(monkeypatch):
    for name in [*REQUIRED, "FREELLMAPI_API_KEY", "CORS_ORIGINS"]:
        monkeypatch.delenv(name, raising=False)
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


@pytest.mark.parametrize("missing", list(REQUIRED))
def test_llm_settings_are_required(env, missing):
    env.delenv(missing)
    with pytest.raises(ValidationError, match=f"(?i){missing}"):
        Settings(_env_file=None)


@pytest.mark.parametrize("empty", list(REQUIRED))
def test_llm_settings_reject_empty_values(env, empty):
    env.setenv(empty, "")
    with pytest.raises(ValidationError, match=f"(?i){empty}"):
        Settings(_env_file=None)


def test_validation_error_does_not_echo_the_api_key(env):
    # Fresh deploy: only the key is set, so the short input dict would be echoed in full.
    for name in REQUIRED:
        env.delenv(name)
    env.setenv("LLM_API_KEY", "nvapi-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert "ABCDEFGH" not in str(error.value)
    assert "0123456789" not in str(error.value)


def test_reads_llm_settings_and_keeps_ingestion_ones(env):
    s = Settings(_env_file=None, profile="gp")
    assert s.llm_model == "large-model"
    assert s.llm_small_model == "small-model"
    assert s.llm_api_key.get_secret_value() == "secret"
    assert s.collection_name() == "gp__nemotron-3-embed-1b"


def test_api_key_alias(env):
    env.delenv("LLM_API_KEY")
    env.setenv("FREELLMAPI_API_KEY", "other")
    assert Settings(_env_file=None).llm_api_key.get_secret_value() == "other"


def test_cors_origins_from_json_list(env):
    env.setenv("CORS_ORIGINS", '["https://a.test", "https://b.test"]')
    assert Settings(_env_file=None).cors_origins == ["https://a.test", "https://b.test"]


def test_api_key_is_not_printed(env):
    assert "secret" not in repr(Settings(_env_file=None))
