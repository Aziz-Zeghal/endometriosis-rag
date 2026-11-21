import pytest
from endorag_ingestion import cli, factory
from endorag_ingestion.core import BasePipeline
from fakes import FakeChunker, FakeConnector, FakeConverter, InMemoryStore
from typer.testing import CliRunner

runner = CliRunner()


class StatsStore(InMemoryStore):
    """InMemoryStore plus the QdrantStore extras the CLI uses."""

    closed = False

    def count(self) -> int:
        return len(self.points)

    def chunk_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for chunk, _ in self.points.values():
            counts[chunk.doc_id] = counts.get(chunk.doc_id, 0) + 1
        return dict(sorted(counts.items()))

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def built(monkeypatch, tmp_path):
    """Replaces build_pipeline and build_storage with fakes; records build_pipeline calls."""
    state = {"store": StatsStore(), "failing": set(), "calls": []}

    def fake_build(settings, refresh=False):
        state["calls"].append((settings, refresh))
        return BasePipeline(
            FakeConnector(tmp_path, state["failing"]),
            FakeConverter(),
            FakeChunker(),
            state["store"],
        )

    monkeypatch.setattr(factory, "build_pipeline", fake_build)
    monkeypatch.setattr(factory, "build_storage", lambda settings: state["store"])
    return state


def test_run_prints_a_table_and_a_summary(built):
    result = runner.invoke(cli.app, ["run", "--profile", "patient"])
    assert result.exit_code == 0, result.output
    assert "ameli-definition" in result.output
    assert "inserm-dossier" not in result.output  # disabled entries are not loaded
    assert " 0 failed" in result.output
    settings, refresh = built["calls"][0]
    assert settings.profile == "patient" and refresh is False
    assert built["store"].closed


def test_run_only_and_refresh_are_passed_through(built):
    result = runner.invoke(
        cli.app, ["run", "--profile", "gp", "--only", "has-imagerie-2025", "--refresh"]
    )
    assert result.exit_code == 0, result.output
    settings, refresh = built["calls"][0]
    assert settings.profile == "gp" and settings.collection_name().startswith("gp__")
    assert refresh is True
    assert built["store"].chunk_counts() == {"has-imagerie-2025": 2}


def test_run_exits_non_zero_when_a_document_fails(built):
    built["failing"].add("ameli-definition")
    result = runner.invoke(cli.app, ["run", "--profile", "patient"])
    assert result.exit_code == 1
    assert "failed" in result.output and "cannot fetch ameli-definition" in result.output


def test_run_rejects_unknown_ids(built):
    result = runner.invoke(cli.app, ["run", "--only", "nope"])
    assert result.exit_code == 2
    assert not built["calls"]


def test_query_prints_ranked_chunks(built):
    runner.invoke(cli.app, ["run", "--only", "ameli-definition"])
    result = runner.invoke(cli.app, ["query", "Qu'est-ce que l'endométriose ?", "--k", "1"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("1. [")
    assert "ameli-definition" in result.output
    assert "2. [" not in result.output


def test_stats_prints_collection_and_counts(built):
    runner.invoke(cli.app, ["run", "--only", "ameli-definition", "--only", "sp-ald"])
    result = runner.invoke(cli.app, ["stats", "--embedder", "other-model"])
    assert result.exit_code == 0, result.output
    assert "collection: patient__other-model" in result.output
    assert "points: 4, documents: 2" in result.output


def test_light_install_imports_without_conversion_dependencies():
    """core, the embedder, the store and build_storage load without the [ingest] extra
    (also guards converter/__init__.py staying import-free: core imports converter.cleaning)."""
    import subprocess
    import sys

    code = """
import sys
from importlib.abc import MetaPathFinder

class Block(MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {"docling", "trafilatura", "torch", "torchvision", "transformers"}:
            raise ImportError(f"blocked: {name}")

sys.meta_path.insert(0, Block())
import endorag_ingestion.core
from endorag_ingestion.cli import app
from endorag_ingestion.embedder import OpenAICompatibleEmbedder
from endorag_ingestion.factory import build_storage
from endorag_ingestion.vector_storage import QdrantStore
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
