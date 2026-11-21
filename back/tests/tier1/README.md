# Tier 1: deterministic tests

Offline and free: no LLM, embedding endpoint or real index. They check logic and wiring
(settings, prompt loading, reasoning stripping, routes with a fake store, the chat
route's AI SDK stream parts with a fake chat service, the safety checks
with a fake model and the keyword regression lists, the conversation graph and the chat
service with scripted chat models and a fake repository: every route, the storyline of
`docs/scenario.md`, model failures; `graph_fakes.py` holds the fakes), never the quality of
generated text. A failure means the code broke, not that a model drifted.

This is the default `pytest` scope (`pytest.ini`) and must stay green on every change.

```bash
pytest back/tests/tier1 -q
```
