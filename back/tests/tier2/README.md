# Tier 2: golden set (live)

Runs the real graph against the LLM endpoint and the local index on curated cases
(question → expected route, cited documents, words that must or must not appear) and
asserts stable properties only, never exact generated text. See
[docs/evaluation.md](../../../docs/evaluation.md).

Not in the default `pytest` scope: tests are marked `@pytest.mark.live` and run on demand,
`pytest back/tests/tier2 -m live`. Cases are added in M3.

`test_retrieval_calibration.py` already runs the questions that calibrated the evidence
threshold (`MIN_DENSE_SCORE`, docs/method.md D-20) on the real patient and GP indexes.

`test_chat_smoke.py` posts storyline turns 1, 4, 7 and 8 to `POST /api/chat` on the real app
(patient profile) and checks the stream shape and routes: a cited answer streamed token by
token, the diagnosis flag, a refusal without sources, the fixed emergency message.
