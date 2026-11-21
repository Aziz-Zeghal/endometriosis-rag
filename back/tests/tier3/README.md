# Tier 3: live guardrails and answer quality

Not in the default `pytest` scope: tests are marked `@pytest.mark.live` and run on demand,
`pytest back/tests/tier3 -m live -s` (`-s` prints each turn's route, flags and duration).
They need the LLM and embedding endpoints (`.env`) and both indexes in `data/qdrant`; the
API must not be running, since local Qdrant locks its directory. See
[docs/evaluation.md](../../../docs/evaluation.md).

**Storyline** (`test_storyline_patient.py`, `test_storyline_gp.py`): the 10 turns of
[docs/scenario.md](../../../docs/scenario.md) on the real app, one conversation per persona
with the history kept as the widget keeps it (Léa turns 1-5, Camille turns 6-8, Dr Hugo
turns 9-10 on the GP profile), plus five edge cases (off-topic, greeting, dose request,
implicit emergency, English question). They assert routes, flags and guardrail-level
properties, never exact wording: cited answers with dated sources and page links, every
`[n]` pointing to a source, no diagnosis statement, score or dose, « vous » only, a
freshness warning on a product, no promise of eligibility, a refusal without sources for a
fact missing from the corpus, the fixed emergency message in under a second, the 2025
imaging update ranked before 2017, an English ESHRE source answered in French.
`storyline.py` holds the conversation helper and the checks. A run takes about 2 minutes.

**RAGAS** (faithfulness, answer relevancy, context precision and recall over the golden
set): a regression signal tracked over time, not a pass/fail gate. Added in M3.
