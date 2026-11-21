# Architecture

Three parts, one direction of data flow:

```
            write side                                   read side
┌──────────────────────────────┐            ┌───────────────────────────────────┐
│ Ingestion (CLI, batch)        │            │ Backend (FastAPI + LangGraph)      │
│ manifest → … → vector store   │ ─────────▶ │ question → graph → streamed answer │
└──────────────────────────────┘   index     └───────────────────────────────────┘
                                                            │ SSE
                                                            ▼
                                             ┌───────────────────────────────────┐
                                             │ Frontend (chat widget, sources)    │
                                             └───────────────────────────────────┘
```

The backend never writes to the index; ingestion never serves users.

## 1. Ingestion pipeline

Data funnel: a few dozen curated sources become a few thousand clean, cited chunks.

```mermaid
flowchart LR
    M[Manifest<br/>YAML: id, url, source, title,<br/>published, licence, audience, format] --> C[Connector<br/>download + cache]
    C --> V[Converter<br/>HTML/PDF/XML → DoclingDocument]
    V --> K[Chunker<br/>docling HybridChunker,<br/>token- and structure-aware]
    K --> S[(Vector storage<br/>embeds with its Embeddings,<br/>then indexes in Qdrant)]
```

| Step | Base class (`core/`) | Input → Output | Default implementation |
|---|---|---|---|
| Connector | `BaseConnector` | `download(entry)`: manifest entry → `RawDocument`, raw bytes cached on disk by the base class | `HttpConnector` (httpx, robots.txt, per-host delay, retries) implements `_download_to()` |
| Converter | `BaseConverter` | `convert(raw)`: raw file → `ConvertedDocument` (docling `DoclingDocument` + Markdown snapshot + metadata), through `_parse` → `_repair` (on failure) → `_enrich` (cleaning) | `HtmlConverter` (trafilatura Markdown parsed by docling's Markdown backend; docling HTML backend as fallback), `PdfConverter` (docling, keeps page numbers), `JatsConverter` (docling JATS), routed by `format` by `RoutingConverter` and cached by `CachedConverter`, which wraps it (`CachedConverter(RoutingConverter())`). Tables of contents are removed by label (`DOCUMENT_INDEX`), and the dot-leader line filter on chunk text catches the rest; the back matter (from the first heading such as References, Sources, Participants, Remerciements, Acknowledgements or a final Contact block to the end) and annexes that are blank report forms (`[<>]` fields) are removed too; page headers and footers are docling furniture, left out of chunks. Web pages also lose share and rating widgets, glossary tooltips and their trailing related-links block (from a heading such as « Voir aussi », « En savoir plus » or « Les autres symptômes » to the end). |
| Chunker | none (single class) | `chunk(document)`: `ConvertedDocument` → `list[Chunk]` | `HybridChunker` (`chunker/hybrid.py`), the only chunker, so it has no base class: docling `HybridChunker` with the embedder's tokenizer (`nvidia/Nemotron-3-Embed-1B-BF16`), at most 512 tokens per chunk headings included, small neighbours under the same headings merged, tables serialized as Markdown tables. Chunk text is cleaned (bullet glyphs, dot leaders, entities, links, table padding) and near-empty chunks are dropped. |
| Embedder | none (single class); subclasses LangChain's `Embeddings` | `embed_documents(list[str])` and `embed_query(str)` → dense vectors. Not a pipeline step: injected into the vector storage. | `OpenAICompatibleEmbedder` (`embedder/openai_compatible.py`), the only embedder: `EMBEDDER` (default `nemotron-3-embed-1b`) through the OpenAI-compatible endpoint, batched, retried and cached on disk; exposes `dimension`. Built by `factory.build_storage` from the settings. Comparing embedding models means changing `EMBEDDER` to another model served by the same endpoint (e.g. `gemini-embedding-001`). LangChain's `Embeddings` interface is kept because it costs nothing and lets other LangChain-based tools (e.g. the RAGAS evaluation) reuse the same embedder. |
| Vector storage | `BaseVectorStore` | `add_documents(chunks)` → ids; `delete_by_metadata(field, value)` → count; `upsert_documents(chunks, key_field="doc_id")` (in the base class: delete per key value, then add); `search(query, k)` → scored chunks | `QdrantStore` (local mode). It **owns its `Embeddings`**, so documents and queries are always embedded by the same model and callers pass text, never vectors. It computes the BM25 sparse vectors itself with fastembed and fuses dense and sparse results with RRF. |

### Design rules

- **Strategy pattern, only where it pays.** A step gets a `Base*` class in `core/` (one
  per file: `base_connector.py`, `base_converter.py`, `base_vector_store.py`,
  `base_pipeline.py`) only where the project shows room for research or new deployments:
  new sources (connector), new formats (converter), another vector database in production
  (vector storage), another pipeline. The chunker (`HybridChunker`) and the embedder
  (`OpenAICompatibleEmbedder`) have a single implementation, so they are plain classes with
  no abstraction; changing the embedding model is a setting (`EMBEDDER`), not a new class.
  Swapping a source or a vector database means instantiating a different class in the
  composition root (`factory.py`). Nothing else changes. This is how the GP profile and
  the production deployment reuse the same code.
- **Template method.** `BasePipeline.run()` owns the sequence and the error handling:
  `_download` → `_convert` → `_chunk` → `_store` (`storage.upsert_documents`, which embeds),
  one document at a time. `BaseConverter.convert()` does the same for a conversion:
  `_parse` (format-specific), `_repair` (optional retry on failure), `_enrich` (a no-op in
  the base; `CleaningConverter`, the base of the format converters, cleans there).
  `RoutingConverter` only routes and keeps that template: its `_parse` and `_repair` go to
  the converter of `entry.format`, and its `_parse` also runs that converter's `_enrich`
  (which receives no entry to route on).
  `close()` releases the connector, the converter and the storage.
- **Decorator.** `CachedConverter` wraps any converter and owns the conversion cache
  (`data/markdown/<id>.md`, `.docling.json`, `.meta.json` with the raw file's sha256 and
  `CONVERTER_VERSION`); the wrapped converter runs only on a cache miss.
- **Per-document fault isolation.** A document that fails to download or convert is logged and
  skipped; the run continues.
- **Idempotent re-ingestion.** `upsert_documents` deletes the existing points whose
  `doc_id` matches (`delete_by_metadata`) before adding the new ones. Point ids are `uuid5(doc_id#chunk_index)`, since Qdrant
  requires UUIDs or integers. Re-running ingestion, even after a page has changed, never
  leaves stale or duplicate chunks.
- **Metadata stays out of the embedded text.** Source, URL, date and heading path live in
  the payload. The embedded text is the chunk content, optionally prefixed with its heading
  path (headings carry meaning; URLs and dates do not).
- **Corpus snapshot committed, index rebuilt.** Fetched pages (`data/raw/<id>.<ext>` +
  `.meta.json`) and converted documents (`data/markdown/<id>.docling.json`, the
  DoclingDocument that gets chunked, plus a readable `<id>.md` and a `.meta.json` recording the
  source hash and converter version) are committed so the demo runs offline or in a Codespace:
  a rebuild runs neither trafilatura nor docling. Chunking only needs the embedder's
  tokenizer (about 17 MB, downloaded once from Hugging Face).
  The vector index (`data/qdrant/`) is gitignored and rebuilt from the snapshot (see
  [sources.md](sources.md#licensing-strategy)).

### Chunk payload

```json
{
  "doc_id": "ameli-traitement",
  "chunk_index": 3,
  "text": "…",
  "heading_path": ["Traitement de l'endométriose", "Traitements hormonaux"],
  "source": "Ameli",
  "title": "Traitement de l'endométriose",
  "url": "https://www.ameli.fr/…",
  "published": "2026-04-09",
  "retrieved": "2026-11-21",
  "audience": "patient",
  "licence": "all-rights-reserved",
  "format": "html | pdf | xml | video",
  "page": null,
  "start_seconds": null
}
```

`doc_id` is the manifest `id`. The golden set references documents by this id.
`page` is the PDF page of the chunk's first item (`null` for HTML and XML); a PDF citation
links to `url#page=N` (`Chunk.citation_url`). The heading path comes from docling's chunk
headings, with the manifest title prepended when the document has no title of its own.
`start_seconds` is only used by the optional video connector
(see [sources.md](sources.md#optional-videos-with-french-captions)).

## Frontend: an embeddable chat widget

The frontend is built as a **widget**, not a full application: a floating chat bubble that
any host page can embed, plus a demo host page (the fictional campaign site).

```html
<!-- On the host site -->
<script src="https://<widget-host>/widget.js" data-api="https://<api-host>" data-profile="patient" defer></script>
```

| Concern | Choice |
|---|---|
| Embedding | One script tag mounts the React widget into a Shadow DOM, so the host page's CSS and the widget's CSS never interfere. An iframe build is the fallback for hosts with a strict Content Security Policy. |
| Configuration | `data-*` attributes: API URL, profile (`patient` or `gp`), initial open state, accent colour. |
| Behaviour | Bubble → panel with banner, disclaimer, streamed answers and source cards linking to the original pages. On a phone the panel goes full screen. |
| Backend contract | Unchanged: the widget calls `POST /api/chat` (AI SDK UI message stream). CORS allows the host origins listed in the backend settings. |
| Demo | `front/` builds both the widget bundle and a fictional campaign page that embeds it. |

## 2. Conversation graph (LangGraph)

```mermaid
flowchart TD
    START((start)) --> SG[safety_gate<br/>red-flag keywords + LLM check]
    SG -->|emergency| EM[emergency<br/>fixed message: 15 / 112 / 3114 / 119]
    SG -->|safe| RT[router<br/>intent classification]
    RT -->|chitchat| CC[chitchat]
    RT -->|out_of_scope| OOS[out_of_scope<br/>polite refusal]
    RT -->|question| RW[rewrite<br/>standalone query from history]
    RW --> RE[retrieve<br/>hybrid search → (rerank) →<br/>threshold → dedup]
    RE -->|enough evidence| GE[generate<br/>cited answer]
    RE -->|weak evidence| TR[triage]
    TR -->|ambiguous| CL[clarify<br/>ask a precise question]
    TR -->|not in corpus| RF[refuse<br/>not covered + see a professional]
    EM --> END((end))
    CC --> END
    OOS --> END
    GE --> END
    CL --> END
    RF --> END
```

### Nodes

| Node | Role | Uses LLM | Output |
|---|---|---|---|
| `safety_gate` | Detects emergencies **before anything else**, on the latest user message. A deterministic French keyword and pattern list runs first. It covers sudden severe pain, fainting, heavy bleeding, high fever with pelvic pain, pain with a possible pregnancy or late period (ectopic pregnancy), sudden one-sided pain (torsion, ruptured cyst) and suicidal thoughts. A small, fast model then double-checks the message. Either can trigger. If the model call fails or times out, the keyword result stands and the answer carries the emergency footer. | Small model | `emergency: bool`, `kind: medical | psychological` |
| `emergency` | Returns the fixed, pre-written message from [scope.md](scope.md#fixed-emergency-message-draft-to-be-reviewed-by-a-health-professional). It is never generated, so it cannot be wrong or slow. | No | Fixed text |
| `router` | Classifies intent: `chitchat`, `out_of_scope`, `question`. Also flags `asks_for_diagnosis` (explicit or implicit, e.g. "c'est normal ?", "mes symptômes correspondent ?") and `asks_for_prescription`, so `generate` applies the right wording. Any health content routes to `question`, even when mixed with a greeting. | Small model, JSON mode | `RouteDecision` |
| `chitchat` | Greetings and thanks, plus a short presentation of what the assistant can do. It is a template, so no ungrounded medical text can come out of it. | No (template) | Text |
| `out_of_scope` | Polite refusal that restates the assistant's scope. | No (template) | Text |
| `rewrite` | Turns a follow-up ("et pendant la grossesse ?") into a standalone query using the last turns. In v1 it only resolves conversation context. Lay vocabulary is handled by dense retrieval, and lay-to-clinical expansion is on the backlog. | Small model | Query string |
| `retrieve` | Hybrid search (dense + BM25, RRF fusion) for top-k candidates, an optional rerank (off in v1), a relevance threshold, then near-duplicate removal. | No | Ranked chunks with scores |
| `generate` | Emits the chunks it was given as sources, then answers **only** from them, in French, with numbered citations `[1]`, `[2]`. If the router flagged a diagnosis or prescription request, it gives general information, never concludes "vous avez / vous n'avez pas", and explicitly refers the user to a health professional. | Main model (Nemotron 3 Ultra) | Streamed text |
| `triage` | Runs when evidence is weak (no chunk above threshold, or too few). Decides between *ambiguous question* and *not in the corpus*. | Small model | `clarify | refuse` |
| `clarify` | Asks one precise follow-up question. | Main model | Text |
| `refuse` | States the information is not in the sources, then refers the user to a professional and to reliable sites. | No (template) | Text |

**Right-sized models.** Classification nodes can use a smaller, faster model
(`LLM_SMALL_MODEL`, for example Nemotron 3 Super; availability to verify). Only
`generate` and `clarify` need the 550B model. This cuts latency and cost without changing
quality where it matters.

### Why emergency comes first

An emergency message must never depend on retrieval quality or on the main model's
behaviour. The gate runs before routing, and the emergency answer is a constant. A
deterministic keyword list guarantees that the known regression cases trigger every
time. The LLM check catches the phrasings the list misses. The keyword list is
illustrative and must be validated by a medical professional before any real use.

### State

```python
class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    emergency: EmergencyDecision | None
    route: RouteDecision | None
    query: str | None
    chunks: list[ScoredChunk]
    triage: Literal["clarify", "refuse"] | None
```

### Streaming contract (backend → frontend)

`POST /api/chat` returns `text/event-stream` in the
[AI SDK UI message stream](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol) format, so the
React side uses an off-the-shelf chat runtime:

| Event part | Emitted by | Content |
|---|---|---|
| `data-route` | `safety_gate`, `router` | Route taken (`emergency`, `question`…) for the UI badge and for tracing |
| `source-url` / `source-document` | `generate` | One per chunk passed to generation: id, title, URL, organisation, date. They are never sent on refuse or clarify answers. |
| `text-start` / `text-delta` / `text-end` | answering nodes | Answer tokens |
| `finish`, then `[DONE]` | API | End of message |

Request body, as sent by the AI SDK transport:
`{"id": "...", "messages": [{"id": "...", "role": "user", "parts": [{"type": "text", "text": "..."}]}]}`.
The last N turns are converted to LangChain `HumanMessage` / `AIMessage`. The response sets
the header `x-vercel-ai-ui-message-stream: v1`.

The graph is streamed with `graph.astream(stream_mode=["messages", "custom"])`. Nodes push
routes and sources with `get_stream_writer()`. Token chunks are filtered by
`langgraph_node`, so the router's JSON never leaks into the answer.

### Prompts

One Markdown file per node in `back/prompts/<profile>/<node>.md`, loaded by name. Prompts are
written in French because they shape the French output; everything else in the repo is in
English.

## Profiles

A **profile** bundles what changes between use cases:

| Profile item | Patient profile | GP profile |
|---|---|---|
| Manifest | `ingestion/manifests/patient.yaml` | `ingestion/manifests/gp.yaml` |
| Qdrant collection | `patient__<embedder>` | `gp__<embedder>` |
| Prompts | `back/prompts/patient/` (plain language, empathetic) | `back/prompts/gp/` (clinical register, red flags, referral criteria) |
| Refusal and emergency wording | Patient-facing | Practitioner-facing |

The profile is selected by configuration (`PROFILE=patient`). The code is identical.
The collection name includes the embedder id, so changing models never mixes vector spaces.

## Backend design patterns

The backend follows the same principles as ingestion: interfaces in `back/src/core/`,
implementations next to them, wiring in one place.

| Pattern | Where | What it buys |
|---|---|---|
| **Strategy** | `Retriever` (hybrid Qdrant), `Reranker` (none in v1; local cross-encoder or a managed reranker later), `ChatModelProvider` (any OpenAI-compatible endpoint), `SafetyCheck` (keyword, LLM) | Swap Qdrant for Azure AI Search, or add a managed reranker such as Cohere, by instantiating another class. The graph code does not change. |
| **Composite** | `CompositeSafetyCheck([KeywordSafetyCheck(), LlmSafetyCheck()])` | Each check stays small and testable. The gate triggers if any check triggers, and a failing check never disables the others. |
| **Template method** | `BaseNode.__call__(state)` runs `_prepare(state)`, then `_execute(...)`, then `_to_update(...)`, with shared logging, timing and error handling. Template answers (`emergency`, `chitchat`, `out_of_scope`, `refuse`) subclass `TemplateNode`, which only declares the prompt file. | Every node behaves the same way on errors and in traces. Adding a node means filling in one or two methods. |
| **Factory** | `back/src/graph/builder.py` builds the graph from `Settings` and the active profile | One place decides which strategies are used |

All data crossing a boundary is a **Pydantic model**: manifest entries, converted documents,
chunks, scored chunks, route and safety decisions, API requests and stream events. Raw
dicts are not passed between modules.

## Repository layout

Three top-level parts, matching the three layers. All Python runs in one conda env.
Each Python part is installed in editable mode with `uv pip install -e`.

```
endometriosis-rag/
├── ingestion/                    # write side
│   ├── pyproject.toml            # package: endorag_ingestion; conversion deps in the [ingest] extra
│   ├── manifests/                # patient.yaml, gp.yaml (URLs + metadata only)
│   ├── src/endorag_ingestion/
│   │   ├── core/                 # base_connector.py, base_converter.py,
│   │   │                         # base_vector_store.py, base_pipeline.py (one Base* class each),
│   │   │                         # models.py (Pydantic), settings.py (see below): contracts only
│   │   ├── connector/            # http_connector.py
│   │   ├── chunker/              # hybrid.py: HybridChunker (docling), the only chunker
│   │   ├── converter/            # html.py (trafilatura), pdf.py and jats.py (docling),
│   │   │                         # routing.py (dispatch on format), cached.py (cache decorator),
│   │   │                         # cleaning.py (site-specific clean-up)
│   │   ├── embedder/             # openai_compatible.py: OpenAICompatibleEmbedder, the only embedder
│   │   ├── vector_storage/       # qdrant.py (dense + BM25, RRF)
│   │   ├── factory.py            # composition root: build_pipeline(settings), build_storage(settings)
│   │   ├── manifest.py           # load and validate the manifests
│   │   └── cli.py                # `endorag-ingest --profile patient`
│   └── tests/
├── back/                         # read side
│   ├── pyproject.toml            # package: endorag_back (depends on endorag_ingestion)
│   ├── prompts/{patient,gp}/     # one .md per node
│   ├── src/endorag_back/
│   │   ├── settings.py
│   │   ├── core/                 # interfaces + Pydantic models: Retriever, Reranker, SafetyCheck,
│   │   │                         # ChatModelProvider, BaseNode, RouteDecision, SafetyDecision, ScoredChunk
│   │   ├── retrieval/            # qdrant_retriever.py, cross_encoder.py
│   │   ├── safety/               # keywords.py, llm_check.py, composite.py
│   │   ├── graph/                # state.py, nodes/, builder.py
│   │   └── api/                  # app.py, routes/chat.py (SSE), routes/health.py, stream.py
│   └── tests/                    # tier 1: safety, routing, nodes (offline)
├── front/                        # Vite + React + TypeScript + assistant-ui: chat widget + demo host page (French UI)
├── eval/                         # golden sets, embedding benchmark, RAGAS runner, reports/
├── data/                         # raw/ and markdown/ (.md + .docling.json) committed; qdrant/ gitignored
├── docs/
├── environment.yml               # conda env (python 3.12); packages installed with uv pip
└── .env.example
```

The back is meant to reuse the ingestion package's settings, embedder (`OpenAICompatibleEmbedder`),
vector storage (`QdrantStore.search`, built with `factory.build_storage`) and models
(`ScoredChunk`, `Chunk`), instead of copying them or manipulating `PYTHONPATH`. The vector space and payload schema
are defined once, on the write side. It depends on plain `endorag-ingestion`, a light
install: docling, trafilatura, PyTorch and transformers are in the `[ingest]` extra, which
only the `run` command needs, and the modules the back imports load none of them (a test
in `test_cli.py` checks it). `core/` depends on nothing in the implementation folders: the
cleaning lives in `converter/cleaning.py` and reaches the pipeline through hooks
(`CleaningConverter._enrich` / `_markdown`, and the chunker's `text_cleaner`, wired in
`factory.py`).

### Settings and paths

Each Python part has a settings module (`core/settings.py` in ingestion) with a
`pydantic-settings` `Settings` class and module-level path constants derived from the repo
root. Nothing hard-codes a path elsewhere.

```python
# ingestion/src/endorag_ingestion/core/settings.py
ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # fetched HTML/PDF cache
MARKDOWN_DIR = DATA_DIR / "markdown"  # converted documents: .md + .docling.json
QDRANT_DIR = DATA_DIR / "qdrant"  # local vector database
MANIFESTS_DIR = ROOT_DIR / "ingestion" / "manifests"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")
    profile: Literal["patient", "gp"] = "patient"
    embedder: str = "nemotron-3-embed-1b"
    qdrant_path: Path = QDRANT_DIR
    chunk_tokenizer: str = "nvidia/Nemotron-3-Embed-1B-BF16"  # the embedder's tokenizer
    chunk_max_tokens: int = 512
    chunk_min_chars: int = 40
    llm_base_url: str
    llm_api_key: SecretStr = Field(
        validation_alias=AliasChoices("LLM_API_KEY", "FREELLMAPI_API_KEY")
    )
```

Every value can be overridden from `.env`. Only `.env.example` is committed.
