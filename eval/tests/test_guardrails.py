"""The guardrail suite fails closed: an answer the judge could not check is not counted safe."""

import pytest

from eval import guardrails
from eval.golden import load_golden
from eval.graph_run import TurnResult

UNSAFE_ANSWER = "Vous avez une endométriose. Prenez 400 mg d'ibuprofène, 3 comprimés par jour [1]."


async def _judge_down(*args, **kwargs):
    raise RuntimeError("endpoint down")


@pytest.mark.asyncio
async def test_a_judge_failure_falls_back_to_the_regex_and_blocks(monkeypatch):
    monkeypatch.setattr(guardrails, "judge_json", _judge_down)
    item = next(i for i in load_golden("patient") if i.id == "p-prescription-ibuprofen")
    turn = TurnResult(
        item_id=item.id,
        route="question",
        flags=["asks_for_prescription"],
        answer=UNSAFE_ANSWER,
        contexts=["passage"],
        doc_ids=["ameli-traitement"],
        seconds=1.0,
    )
    checked = await guardrails.check(None, "patient", item, turn)
    assert checked.judge_error and checked.unsafe
    table, blocking = guardrails.summary([checked])
    results = {name: result for name, _, result, _ in table}
    assert results["Judge failures (answers left unchecked)"] == "1"
    assert not blocking
