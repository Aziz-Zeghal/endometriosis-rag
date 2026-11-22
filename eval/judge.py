"""The judge model: another model family than the generator (Nemotron), on the same
OpenAI-compatible endpoint, and the embeddings RAGAS reuses from retrieval.

Checked on the endpoint on 2026-11-21: `claude-haiku-4-5` returned valid JSON to 4 of 4
statement-extraction prompts and ran the three RAGAS metrics; `gemini-3-flash-preview`
answered the probes but truncated its JSON inside RAGAS; the DeepSeek, GLM, Kimi, Qwen,
Mistral and GPT models tried from `/v1/models` had no usable provider (503) or timed out.
The probes were one-off calls and are not kept in the repository.
"""

import asyncio
import json

from endorag_back.config.settings import Settings
from endorag_ingestion.embedder import OpenAICompatibleEmbedder
from openai import AsyncOpenAI
from ragas.embeddings.base import BaseRagasEmbedding

JUDGE_MODEL = "claude-haiku-4-5"


def judge_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout=120,
    )


async def judge_json(client: AsyncOpenAI, prompt: str) -> dict:
    """One judge call that must return a JSON object (a fenced block is accepted)."""
    reply = await client.chat.completions.create(
        model=JUDGE_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0
    )
    text = (reply.choices[0].message.content or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


class RagasEmbedding(BaseRagasEmbedding):
    """Our retrieval embedder (batched, retried, cached) behind the RAGAS embedding interface."""

    def __init__(self, settings: Settings) -> None:
        self._inner = OpenAICompatibleEmbedder(
            settings.embedder, settings.llm_base_url, settings.llm_api_key.get_secret_value()
        )

    def embed_text(self, text: str, **kwargs) -> list[float]:
        return self._inner.embed_query(text)

    async def aembed_text(self, text: str, **kwargs) -> list[float]:
        return await asyncio.to_thread(self._inner.embed_query, text)
