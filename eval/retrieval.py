"""Retrieval benchmark: Hit@5 and MRR@10 per profile, embedder and wording (lay vs medical).

    python -m eval.retrieval            # writes eval/reports/retrieval.md

Each embedder has its own collection (`<profile>__<embedder>`), built beforehand with
`endorag-ingest run --profile <p> --embedder <model>`. Questions: the in-corpus golden items
with no history (a follow-up is not a standalone query). Ranks are measured at document
level: the distinct `doc_id`s of the 20 candidates, in order, against `reference_doc_ids`.
Needs the embedding endpoint and `data/qdrant` (the backend must not be running).
"""

import statistics
import time
from datetime import date
from pathlib import Path

from endorag_back.config.settings import Settings
from endorag_back.repositories.search_repository import SearchRepository
from endorag_ingestion.core import ScoredChunk
from endorag_ingestion.factory import build_storage
from endorag_ingestion.manifest import load_manifest
from endorag_ingestion.vector_storage import QdrantStore
from endorag_ingestion.vector_storage.qdrant import DENSE
from pydantic import BaseModel

from eval.golden import GoldenItem, load_golden

EMBEDDERS = ["nemotron-3-embed-1b", "gemini-embedding-001"]
PROFILES = ["patient", "gp"]
CANDIDATES = 20
REPORT = Path(__file__).parent / "reports" / "retrieval.md"


class QueryResult(BaseModel):
    item_id: str
    wording: str
    rank_hybrid: int | None  # 1-based rank of the first reference document, None if absent
    rank_dense: int | None
    served_hit: bool  # a reference document among the chunks `retrieve` hands to `generate`
    seconds: float  # hybrid search latency (query embedding included)


def doc_ranking(hits: list[ScoredChunk]) -> list[str]:
    return list(dict.fromkeys(hit.chunk.doc_id for hit in hits))


def first_rank(ranking: list[str], relevant: set[str]) -> int | None:
    return next((i for i, doc in enumerate(ranking, start=1) if doc in relevant), None)


def hit_at(ranks: list[int | None], k: int) -> float:
    return sum(r is not None and r <= k for r in ranks) / len(ranks)


def mrr_at(ranks: list[int | None], k: int) -> float:
    return sum(1 / r for r in ranks if r is not None and r <= k) / len(ranks)


def matched_pairs(results: list[QueryResult]) -> list[QueryResult]:
    """The items of the lay / medical pairs (`<stem>-lay` and `<stem>-medical`, same need)."""
    stems = {r.item_id.removesuffix(f"-{r.wording}") for r in results}
    paired = {s for s in stems if {f"{s}-lay", f"{s}-medical"} <= {r.item_id for r in results}}
    return [r for r in results if r.item_id.removesuffix(f"-{r.wording}") in paired]


def dense_search(store: QdrantStore, query: str, k: int) -> list[str]:
    """Dense-only ranking, to compare the embedders without the shared BM25 half."""
    vector = store.embedding.embed_query(query)
    points = store.client.query_points(
        store.collection, query=vector, using=DENSE, limit=k, with_payload=["doc_id"]
    ).points
    return list(dict.fromkeys(p.payload["doc_id"] for p in points))


def run(profile: str, embedder: str, items: list[GoldenItem]) -> list[QueryResult]:
    settings = Settings(profile=profile, embedder=embedder)
    store = build_storage(settings)
    try:
        expected = {e.id for e in load_manifest(profile) if e.enabled}
        if missing := expected - set(store.chunk_counts()):
            raise RuntimeError(f"collection incomplete, missing {', '.join(sorted(missing))}")
        repo = SearchRepository(store, settings)
        results = []
        for item in items:
            relevant = set(item.reference_doc_ids)
            started = time.perf_counter()
            hits = store.search(item.user_input, k=CANDIDATES)
            seconds = time.perf_counter() - started
            served = repo.retrieve(item.user_input).chunks
            results.append(
                QueryResult(
                    item_id=item.id,
                    wording=item.wording,
                    rank_hybrid=first_rank(doc_ranking(hits), relevant),
                    rank_dense=first_rank(
                        dense_search(store, item.user_input, CANDIDATES), relevant
                    ),
                    served_hit=any(hit.chunk.doc_id in relevant for hit in served),
                    seconds=seconds,
                )
            )
        return results
    finally:
        store.close()


def _row(label: str, results: list[QueryResult]) -> str:
    hybrid = [r.rank_hybrid for r in results]
    dense = [r.rank_dense for r in results]
    served = sum(r.served_hit for r in results) / len(results)
    latency = statistics.median(r.seconds for r in results)
    return (
        f"| {label} | {len(results)} | {hit_at(hybrid, 5):.2f} | {mrr_at(hybrid, 10):.2f} | "
        f"{hit_at(dense, 5):.2f} | {mrr_at(dense, 10):.2f} | {served:.2f} | {latency:.2f} |"
    )


def _rank(rank: int | None) -> str:
    return "-" if rank is None else str(rank)


def render(
    results: dict[tuple[str, str], list[QueryResult] | str], questions: dict[str, str]
) -> str:
    lines = [
        "# Retrieval benchmark",
        "",
        f"Generated by `python -m eval.retrieval` on {date.today().isoformat()}. Method: "
        "[docs/evaluation.md](../../docs/evaluation.md#embedding-benchmark).",
        "",
        "Document-level ranks over the distinct documents of the 20 hybrid candidates "
        "(dense + BM25, RRF). **Hybrid** is what the app runs; **dense** ranks with the "
        "embedder alone, which isolates the model (BM25 is identical for both). **Served "
        "Hit@5**: a reference document among the 5 chunks `retrieve` passes to `generate` "
        "(after near-duplicate removal and the 2-chunks-per-document cap). Latency: median "
        "hybrid search time, query embedding included (the query cache is warm after a "
        "first run). **Matched pairs**: the same need asked in lay and in medical words "
        "(`<topic>-lay` / `<topic>-medical`), which is how the lay / medical gap is read; "
        "the all-items split also contains unpaired questions (storyline turns, requests on "
        "the lay side; myth, rights, safety on the medical side).",
        "",
    ]
    for profile in PROFILES:
        lines += [
            f"## {profile}",
            "",
            "| Embedder / wording | n | Hit@5 hybrid | MRR@10 hybrid | Hit@5 dense | "
            "MRR@10 dense | Served Hit@5 | Latency (s) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        measured = [e for e in EMBEDDERS if isinstance(results[(profile, e)], list)]
        for embedder in EMBEDDERS:
            res = results[(profile, embedder)]
            if isinstance(res, str):
                lines.append(f"| **{embedder}** | not measured: {res} | | | | | | |")
                continue
            lines.append(_row(f"**{embedder}**, all", res))
            for label, pool in (("matched pairs", matched_pairs(res)), ("all items", res)):
                for wording in ("lay", "medical"):
                    subset = [r for r in pool if r.wording == wording]
                    if subset:
                        lines.append(_row(f"{embedder}, {wording} ({label})", subset))
        lines += [
            "",
            "Rank of the first reference document (hybrid / dense), per question:",
            "",
            "| Question | Wording | " + " | ".join(measured) + " |",
            "|---|---|" + "---|" * len(measured),
        ]
        by_model = {e: {r.item_id: r for r in results[(profile, e)]} for e in measured}
        for item_id in by_model[measured[0]] if measured else []:
            r0 = by_model[measured[0]][item_id]
            ranks = [by_model[e][item_id] for e in measured]
            cells = [f"{_rank(r.rank_hybrid)} / {_rank(r.rank_dense)}" for r in ranks]
            lines.append(
                f"| `{item_id}` {questions[item_id]} | {r0.wording} | {' | '.join(cells)} |"
            )
        lines.append("")
    lines += [
        "## Limits",
        "",
        "- Small sample (tens of questions per profile): one question moves Hit@5 by several "
        "points, so gaps under about 10 points are within noise.",
        "- The lay / medical gap on matched pairs rests on few pairs (9 patient, 3 GP): one "
        "question is 11 points on the patient pairs.",
        "- Questions are searched as typed. In the app, `rewrite` only changes follow-ups, so "
        "follow-up items are left out here.",
        "- A hit means one reference document is retrieved, not that the passage answering the "
        "question is; RAGAS context precision covers that (eval/reports/ragas.md).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    results: dict[tuple[str, str], list[QueryResult] | str] = {}
    questions: dict[str, str] = {}
    for profile in PROFILES:
        items = [i for i in load_golden(profile) if i.in_corpus and not i.history]
        questions |= {i.id: i.user_input for i in items}
        for embedder in EMBEDDERS:
            try:
                results[(profile, embedder)] = run(profile, embedder, items)
                print(_row(f"{profile} {embedder}", results[(profile, embedder)]))
            except Exception as exc:  # e.g. the endpoint's daily embedding quota
                results[(profile, embedder)] = f"{type(exc).__name__}: {str(exc)[:120]}"
                print(f"{profile} {embedder}: not measured ({results[(profile, embedder)]})")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(results, questions), encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
