# Local demo vs production

The demo runs on one workstation (RTX 5060 Ti, 16 GB) with the LLM reached through an
OpenAI-compatible endpoint. Production targets **Azure**, first because Azure is certified
**HDS** (Hébergeur de Données de Santé), which French law (Code de la santé publique,
L.1111-8) requires for hosting personal health data. AWS and GCP also advertise HDS
certification, so the design is not locked in.

Every swap below is a configuration change or a different implementation of an
existing `core/` interface. The graph, the prompts and the API contract do not change.

## Component mapping

| Layer | Local demo | Production (Azure) | AWS / GCP equivalent | Why |
|---|---|---|---|---|
| Generation LLM | Nemotron 3 Ultra via an OpenAI-compatible API | Nemotron 3 Ultra **NIM** on Microsoft Foundry (listed GA), or NIM on AKS | Bedrock / SageMaker NIM · Vertex AI Model Garden, NIM on GKE | Same model and same OpenAI-compatible API, so only `base_url` changes. Managed quotas, RBAC, EU region. |
| Classifier LLM | Smaller model via the same API | Nemotron 3 Super / Nano NIM, or a small Foundry model | Same | Low latency for routing and safety checks |
| Embeddings | Nemotron-3-Embed-1B through an OpenAI-compatible API (NVIDIA NIM) | Same model served by Text Embeddings Inference or a NIM on AKS GPU nodes, or a Foundry embedding endpoint | SageMaker endpoint · Vertex AI | Embeddings must stay in-region under a contract that covers health-related queries. A model change means a full reindex, so the index name carries the model id. |
| Vector store | Qdrant local mode (file on disk) | **Azure AI Search** (hybrid + RRF included, semantic ranker), or **Elasticsearch** on Elastic Cloud (Azure native ISV) | OpenSearch Service · Vertex AI Vector Search | Azure AI Search is first-party, so inside Azure's HDS scope, and hybrid search needs no licence tier. Elasticsearch gives richer relevance tuning, but its native RRF needs Enterprise and its HDS status is unconfirmed. Qdrant server/Cloud is the zero-code-change option. |
| Reranker | None in v1 (hybrid search with RRF) | **Cohere Rerank** in Microsoft Foundry | Cohere / Amazon Rerank on Bedrock · Vertex AI Ranking API | No GPU nodes needed just for reranking; pay per call. Preview models are outside the HDS scope, and GA availability is **to verify**. The fallback is Azure AI Search's built-in semantic ranker (first-party). |
| Backend | uvicorn on the workstation | **Azure Container Apps** (scale to zero, revisions, managed identity), then AKS if GPU NIMs are self-hosted | ECS Fargate / App Runner · Cloud Run | The same Docker image everywhere |
| Frontend | Vite dev server (widget + demo host page) | **Azure Static Web Apps** or Blob + Front Door serving `widget.js` from a CDN; host sites embed it with one script tag | Amplify / S3 + CloudFront · Firebase Hosting | A static bundle is cheap and CI-native; the API restricts CORS to the host origins. The demo page loads no third-party font or script (system font stack), so visitors' IP addresses reach no other service; a production page would self-host its fonts |
| Ingestion | CLI run by hand | **Container Apps Jobs** (scheduled), raw documents versioned in **Blob Storage** | ECS scheduled tasks + S3 · Cloud Run Jobs + GCS | The same CLI code runs as a job. Blob versioning keeps the provenance of every cited document. |
| Observability | Logs, optional LangSmith traces | **Langfuse self-hosted** on Azure + Azure Monitor (OpenTelemetry) | CloudWatch / X-Ray · Cloud Trace | Per-request traces (query, chunks, scores, answer, latency) without sending health questions to a third-party SaaS |
| Safety | Keyword gate + LLM classifier + prompt rules | Add **Azure AI Content Safety** (self-harm and violence classifiers, French supported) and/or **NeMo Guardrails** / Nemotron safety models (check NGC support status) | Bedrock Guardrails · Model Armor | Defence in depth, especially self-harm detection for a chronic-pain population |
| Secrets | `.env` (gitignored) | **Azure Key Vault** + managed identity | Secrets Manager · Secret Manager | No secrets in images or the repo; rotation and audit |
| CI/CD | `ruff`, `pytest`, eval scripts run locally | **GitHub Actions**: lint, tests, guardrail suite, RAG evaluation gate, image build, deploy via OIDC | Same, with IAM OIDC / Workload Identity | No long-lived cloud credentials; quality regressions block the merge |
| Auth | None | Anonymous by default; **Entra External ID** only if accounts are added | Cognito · Identity Platform | Without accounts, we store no identifiable health data. Accounts bring HDS and GDPR duties. |

## Scaling path

| Stage | Users | What changes |
|---|---|---|
| **Demo** (now) | 1 | Everything local except the LLM |
| **Pilot** | Hundreds | Containerize the API, move to managed vector search, scheduled ingestion, tracing, evaluation in CI |
| **Production** | Tens of thousands | Autoscaling Container Apps, semantic cache for frequent questions, managed reranker, content safety, a corpus governance workflow with medical review, DPIA completed |

## Compliance notes

- **HDS**: Azure holds HDS v2.0 (certificate issued October 2025) for ISO 27001-scoped
  services in EEA regions, including France Central, France South, West Europe and Sweden
  Central.
  Preview services are excluded. HDS terms must be signed contractually.
- **GDPR**: health data is an Article 9 special category. A real deployment needs a DPIA,
  a legal basis, data minimisation, retention limits, and a DPA with every sub-processor.
- **Open question for legal review**: whether anonymous chatbot questions count as personal
  health data. The safe default is to store nothing identifiable.

## Improvement backlog

| Improvement | Value | Effort |
|---|---|---|
| Lay-to-clinical query expansion ("règles douloureuses" → dysménorrhée) | Better recall on lay phrasing | S |
| Audience-aware retrieval (patient vs GP filter on one index) | One index for both profiles | S |
| Feedback buttons logged into traces | Bad answers feed the golden set | S |
| Semantic cache for frequent questions | Latency and cost on a 550B model | S–M |
| Structure-aware chunking of guidelines (keep the recommendation grade as metadata) | Answers can state the strength of evidence | M |
| Evaluation gate in CI (RAGAS + guardrail suite) | Prevents regressions | M |
| Dedicated guardrail models (Nemotron safety models, check NGC support status; Azure Content Safety) | Stronger self-harm and abuse detection | M |
| Video and podcast transcripts with timestamps (beyond the optional v1 connector) | Richer, more accessible sources | M |
| Corpus governance: scheduled re-ingestion, diff detection when HAS or ESHRE update guidance, medical review queue | Answers stay current and validated | M |
| Accessibility (RGAA / WCAG 2.2 AA, easy-to-read mode, voice input) | Fatigue and pain make typing hard | M |
| Smaller widget: a tiny loader for the bubble, the chat panel (React, assistant-ui) lazy-loaded on first open | `widget.js` is 355 kB gzipped; host pages load almost nothing until the bubble is used | S |
| Consultation preparation export (symptom summary and questions for the doctor) | High patient value without diagnosing | M |
| Opt-in personalization (symptom journal) | Tailored explanations; requires accounts, consent and HDS | L |
