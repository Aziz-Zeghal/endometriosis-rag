"""Offline checks of the benchmark helpers: document-level ranks, Hit@k, MRR@k, final route."""

from types import SimpleNamespace

from pytest import approx

from eval.graph_run import final_route
from eval.retrieval import QueryResult, first_rank, hit_at, matched_pairs, mrr_at


def test_first_rank_is_one_based_and_none_when_absent():
    ranking = ["a", "b", "c"]
    assert first_rank(ranking, {"c", "b"}) == 2
    assert first_rank(ranking, {"z"}) is None


def test_hit_and_mrr_respect_the_cutoff():
    ranks = [1, 3, 7, None]
    assert hit_at(ranks, 5) == 0.5
    assert mrr_at(ranks, 5) == approx((1 + 1 / 3) / 4)
    assert mrr_at(ranks, 10) == approx((1 + 1 / 3 + 1 / 7) / 4)


def test_matched_pairs_keep_only_items_with_both_wordings():
    def result(item_id, wording):
        return QueryResult(
            item_id=item_id,
            wording=wording,
            rank_hybrid=1,
            rank_dense=1,
            served_hit=True,
            seconds=0.0,
        )

    results = [
        result("p-fatigue-lay", "lay"),
        result("p-fatigue-medical", "medical"),
        result("p-story-1", "lay"),
        result("p-urinary-lay", "lay"),
        result("p-myth-pregnancy", "medical"),
    ]
    assert [r.item_id for r in matched_pairs(results)] == ["p-fatigue-lay", "p-fatigue-medical"]


def _state(emergency=False, route="question", sufficient=True, triage=None):
    return {
        "emergency": SimpleNamespace(emergency=emergency),
        "route": SimpleNamespace(route=route),
        "sufficient": sufficient,
        "triage": triage,
    }


def test_final_route_is_the_route_the_client_keeps():
    assert final_route(_state(emergency=True)) == "emergency"
    assert final_route(_state(route="out_of_scope", sufficient=None)) == "out_of_scope"
    assert final_route(_state()) == "question"
    assert final_route(_state(sufficient=False, triage="refuse")) == "refuse"
