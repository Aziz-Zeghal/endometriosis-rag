# Tech stack

Versions were checked on 2026-11-20 and serve as lower bounds. Each choice has a
one-line justification.

## Summary

| Layer | Choice | Rather than | Because |
|---|---|---|---|
| Generation LLM | **Nemotron 3 Ultra** (550B total, ~55B active, MoE) via an OpenAI-compatible API | A local 7–30B model | Much higher answer quality in French with no GPU cost. The OpenAI-compatible API keeps us provider-agnostic: only `base_url` changes in production. |
| Classifier LLM | **A smaller model on the same endpoint** (e.g. Nemotron 3 Super 120B, availability to verify) | The 550B model for every node | Routing and safety checks are short classification tasks, so a smaller model lowers latency. |
| LLM client | `langchain-openai` `ChatOpenAI(base_url=…)` | A provider-specific SDK | The endpoint speaks the OpenAI API, and LangGraph integrates natively. |
| Structured output | `with_structured_output(..., method="json_mode", include_raw=True)` | `json_schema` / tool calling | Support for strict JSON schema across endpoints is unconfirmed. JSON mode plus schema-in-prompt is portable, and `include_raw` lets us fall back safely on parse errors. |
| Orchestration | **LangGraph** ≥ 1.2 | A linear LangChain chain | Safety routing and refuse-vs-clarify branches read naturally as a graph, and the graph is also the documentation. |
| API | **FastAPI** ≥ 0.165 + uvicorn | Flask | Async streaming, typed models, OpenAPI docs for free. |
| Streaming | `StreamingResponse` emitting the AI SDK UI message stream | `sse-starlette`, LangGraph Server | The protocol is a handful of `data:` lines, so no extra dependency or server is needed, and the frontend gets typed source parts. |
| Embeddings | **Nemotron-3-Embed-1B through the OpenAI-compatible endpoint** (default, served by NVIDIA NIM); `gemini-embedding-001` as the API alternative; the same Nemotron weights locally (`[local]` extra) as the offline fallback | Local GPU models by default | Best French retrieval scores on the shortlist, no model download or GPU needed, identical locally and in a Codespace. Requests are batched (16 texts), retried with backoff and cached on disk, so an interrupted run resumes without re-embedding. |
| Reranker | **None in v1**, behind a `Reranker` interface | A local cross-encoder by default | Hybrid search with RRF is a strong baseline for a few hundred chunks. If the benchmark shows a gap, `BAAI/bge-reranker-v2-m3` (Apache-2.0, `[local]` extra) is the candidate; jina-reranker-v3 is CC BY-NC. |
| Vector store | **Qdrant, local mode** (`QdrantClient(path=…)`) | Chroma, FAISS, Elasticsearch | Qdrant is the only embedded option with **native hybrid search** (dense + sparse BM25, RRF fusion). The same client code runs against a Qdrant server or Qdrant Cloud. Chroma has no hybrid search in local mode. FAISS is an index, not a database. Elasticsearch needs a JVM container, and its RRF retriever requires an Enterprise licence. |
| Sparse retrieval | BM25 sparse vectors via `fastembed` (`Qdrant/bm25`, French stemming **(to verify)**) | No lexical search | Exact medical terms (diénogest, adénomyose, endométriome) are where dense retrieval fails. |
| PDF conversion | **docling** ≥ 2.151 | pymupdf4llm, unstructured | A layout model recovers real section headings for heading-aware chunks. It needs PyTorch, installed as the CPU build: fast enough for a dozen PDFs. pymupdf4llm is AGPL **(to verify)**. |
| HTML conversion | **trafilatura** ≥ 2.3 (Markdown output) | docling's HTML backend, markitdown | trafilatura strips navigation, footers and cookie banners, which the others keep. Heading preservation must be checked on day 1 **(to verify)**. |
| Chunking | docling **`HybridChunker`** with the embedder's tokenizer (`nvidia/Nemotron-3-Embed-1B-BF16`), 512 tokens max, `merge_peers=True` | LangChain splitters (`MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter`), chonkie | Token-aware with the embedder's own tokenizer, structure-aware (sections, lists, tables, heading path kept for citations), and it keeps page provenance for page-level citations of PDFs. HTML goes through the same chunker: trafilatura's Markdown is parsed by docling's Markdown backend. |
| Fetching | `httpx` + `urllib.robotparser` + per-host delay + disk cache | Scrapy | A few dozen known URLs: a cached, rate-limited loop is short and reproducible offline. |
| Config | `pydantic-settings` (`.env`, `SecretStr`) | `os.getenv` | Typed, validated config, and secrets stay out of logs. Only `.env.example` is committed. |
| Frontend build | **Vite + React 19 + TypeScript** | Streamlit, Next.js | A single-page app with no server-side rendering needs. One frontend rather than Streamlit first and React later avoids building the UI twice. |
| Chat UI | **assistant-ui** with its AI SDK runtime (`@assistant-ui/react-ai-sdk`) | Hand-written chat, CopilotKit, LangGraph `useStream` | Thread, streaming Markdown, auto-scroll, cancel and retry come ready-made. It reads a protocol our FastAPI can emit. `useStream` expects a LangGraph Server. |
| UI kit | **shadcn/ui + Tailwind CSS v4** | MUI, Chakra | assistant-ui components are shadcn-based, so they need no theming work. |
| Evaluation | **ragas** ≥ 0.4.4 (collections API) | A custom LLM judge | Standard metrics that people recognise, with a pluggable OpenAI-compatible judge and local embeddings. |
| Tracing (optional) | LangSmith, enabled by environment variables only | None | Zero-code traces of every node for debugging and the demo. Self-hosted Langfuse is the production option (see [local-vs-production.md](local-vs-production.md)). |
| Python env | **conda** (Python 3.12) + **uv pip** + **ruff** | `uv sync`, `.venv`, pip | conda supplies the interpreter and the CUDA-friendly environment. `uv pip install -e .` installs into the active conda env (it targets `CONDA_PREFIX`) and never creates `.venv`. ruff handles lint and format. |
| Node tooling | npm | pnpm | Nothing extra to install for someone cloning a public repo with a single frontend package. |

## LLM endpoint

- Any OpenAI-compatible endpoint (NVIDIA API catalog, a NIM, a gateway), configured with
  `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`, plus `LLM_SMALL_MODEL` for
  classifiers.
- Reasoning models may return their reasoning separately or inline (`<think>` tags). The
  backend strips any inline reasoning before streaming.
- To check before relying on them: whether `response_format={"type":"json_object"}` is
  honoured, the streaming behaviour, which smaller chat models are available, and the
  latency of the large vs the small model.

## Embedding shortlist

The default is `nemotron-3-embed-1b` through the API. Local candidates are optional and run
on the CPU build of PyTorch (a few hundred chunks take minutes); a GPU only speeds them up.

The endpoint sends the same `input_type` for documents and queries, so the embeddings are
symmetric. The local fallback reproduces this by using the same prompt on both sides, which
keeps API and local vectors in the same space.

| Model | Params | Dims | Max tokens | Memory (fp16, est.) | Licence | Why on the list |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3-Embedding-4B` | 4B | 2560 (MRL) | 32k | ~8 GB | Apache-2.0 | Strongest open model that fits on Alloprof (65.4), Syntec (89.9) and MIRACL-HN fr (60.2) nDCG@10 (MTEB results repo). Instruction prefix on queries only. |
| `nvidia/Nemotron-3-Embed-1B-BF16` (**default, via API**) | 1.1B | 2048 | 32k | ~2.3 GB | OpenMDW-1.1 (commercial OK) | 2026 NVIDIA model. Leads on the French RTEB tasks (French1 88.8, FrenchLegal1 94.6), even ahead of Qwen3-4B. Has no Alloprof or Syntec results. Needs recent sentence-transformers/transformers. `query:` / `passage:` prefixes. |
| `BAAI/bge-m3` | ~0.57B | 1024 | 8k | ~1.1 GB | MIT | Robust baseline, no prefixes, widely known. |
| `gemini-embedding-001` (API) | API | 3072 (MRL) | 2k | 0 | Proprietary API | API alternative with strong French scores. Trade-off: data leaves the machine. |

Notes:
- `nvidia/Nemotron-3.5-Embed-1B` (Oct 2026) exists but publishes no text-retrieval French
  scores and targets multimodal documents. It is a stretch candidate only.
- The 8B models (Qwen3-Embedding-8B, Nemotron-3-Embed-8B) are too slow on CPU and are
  not on the list.
- Method: [evaluation.md](evaluation.md#embedding-benchmark).

## Python environment

docling is the only dependency that needs PyTorch. `ingestion/pyproject.toml` pins `torch`
and `torchvision` to the CPU wheel index through `[tool.uv.sources]`, so no CUDA wheels are
downloaded.

```bash
conda env create -f environment.yml        # python 3.12 only, env name: endorag
conda activate endorag
uv pip install -e "./ingestion[dev]" -e "./back[dev]"
uv pip install -e "./ingestion[local]"     # optional: local embedding models
uv pip install -r eval/requirements.txt    # ragas, only for evaluation
ruff check . && ruff format --check .
```

## Known risks

| Risk | Mitigation |
|---|---|
| The LLM endpoint is slow or unavailable | Timeouts, a fallback to a smaller model, a pre-recorded walkthrough as a last resort |
| The router returns invalid JSON | `include_raw=True`, then fall back to the `question` route. The safety keyword gate does not depend on the LLM. |
| trafilatura drops headings | Fall back to docling on the HTML, or chunk without headings |
| assistant-ui does not render source parts the way we want | A small custom `Sources` component reading message parts, or fall back to `@ai-sdk/react` `useChat` |
| The RAGAS judge prompts are in English and the answers in French | Read scores as relative across iterations, and use a judge model different from the generator |
