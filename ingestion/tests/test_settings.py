from endorag_ingestion.core.settings import MANIFESTS_DIR, ROOT_DIR, Settings


def test_root_dir_is_repo_root():
    assert (ROOT_DIR / "ingestion" / "pyproject.toml").is_file()
    assert MANIFESTS_DIR.is_dir()


def test_collection_name_includes_profile_and_embedder():
    s = Settings(_env_file=None, profile="gp", embedder="BAAI/bge-m3")
    assert s.collection_name() == "gp__BAAI_bge-m3"


def test_api_key_alias(monkeypatch):
    monkeypatch.setenv("FREELLMAPI_API_KEY", "secret")
    s = Settings(_env_file=None)
    assert s.llm_api_key is not None
    assert s.llm_api_key.get_secret_value() == "secret"
