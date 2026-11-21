"""`endorag-ingest`: build the index (run), check it (query, stats). Logs go to stderr."""

import logging
import sys
from typing import Annotated

import typer

from endorag_ingestion import factory
from endorag_ingestion.core.settings import Profile, Settings
from endorag_ingestion.manifest import load_entries

app = typer.Typer(add_completion=False, no_args_is_help=True)

ProfileOpt = Annotated[Profile, typer.Option(help="Corpus profile (manifest and collection).")]
EmbedderOpt = Annotated[str | None, typer.Option(help="Override the embedder from .env.")]


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    """Ingestion pipeline: manifest -> download -> convert -> chunk -> embed -> Qdrant."""
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Per-request lines from HTTP libraries drown the per-document status.
    # "httpx2" is the logger of the httpx copy bundled with openai: it would print the endpoint URL.
    for name in ("httpx", "httpx2", "openai", "docling", "RapidOCR"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _settings(profile: str, embedder: str | None) -> Settings:
    overrides = {"profile": profile}
    if embedder:
        overrides["embedder"] = embedder
    return Settings(**overrides)


@app.command()
def run(
    profile: ProfileOpt = "patient",
    only: Annotated[list[str] | None, typer.Option(help="Only these doc ids.")] = None,
    refresh: Annotated[bool, typer.Option(help="Re-fetch cached raw files.")] = False,
    embedder: EmbedderOpt = None,
) -> None:
    """Ingest a profile's manifest into its collection."""
    settings = _settings(profile, embedder)
    try:
        entries = load_entries(profile, only or None)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--only") from exc
    try:
        pipeline = factory.build_pipeline(settings, refresh=refresh)
    except ImportError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    try:
        summary = pipeline.run(entries)
        total = pipeline.storage.count()
    finally:
        pipeline.close()

    typer.echo(f"{'doc_id':<32} {'status':<8} {'chunks':>6}  error")
    for r in summary.results:
        typer.echo(f"{r.doc_id:<32} {r.status:<8} {r.chunks:>6}  {r.error or ''}")
    chunks = sum(r.chunks for r in summary.results)
    typer.echo(
        f"\n{settings.collection_name()}: {summary.ok} ok, {summary.failed} failed, "
        f"{summary.skipped} skipped, {chunks} chunks ingested, {total} points in collection"
    )
    if summary.failed:
        raise typer.Exit(code=1)


@app.command()
def query(
    text: str,
    profile: ProfileOpt = "patient",
    k: Annotated[int, typer.Option(help="Number of chunks.")] = 5,
    embedder: EmbedderOpt = None,
) -> None:
    """Hybrid search (dense + BM25) and print the top chunks with their sources."""
    storage = factory.build_storage(_settings(profile, embedder))
    try:
        hits = storage.search(text, k=k)
    finally:
        storage.close()
    for rank, hit in enumerate(hits, 1):
        c = hit.chunk
        typer.echo(f"{rank}. [{hit.score:.4f}] {c.doc_id}  ({c.source}, {c.published})")
        typer.echo(f"   {' > '.join(c.heading_path)}")
        typer.echo(f"   {c.citation_url}")
        typer.echo(f"   {' '.join(c.text.split())[:200]}\n")


@app.command()
def stats(profile: ProfileOpt = "patient", embedder: EmbedderOpt = None) -> None:
    """Collection name, number of points and chunks per document."""
    settings = _settings(profile, embedder)
    storage = factory.build_storage(settings)
    try:
        total = storage.count()
        counts = storage.chunk_counts()
    finally:
        storage.close()
    typer.echo(f"collection: {settings.collection_name()}")
    typer.echo(f"points: {total}, documents: {len(counts)}")
    for doc_id, n in counts.items():
        typer.echo(f"  {doc_id:<32} {n:>6}")
