# endometriosis-rag

A French-language question-answering assistant on endometriosis, grounded in a curated
corpus of public health sources. Every answer cites its sources. The assistant never
diagnoses or prescribes, declines when the answer is not in the corpus, and redirects
emergencies to 15 / 112.

> **Fictional scenario.** This is a technical demonstrator built around a hypothetical
> public-health awareness campaign ([docs/scenario.md](docs/scenario.md)). No real ministry,
> agency, health insurer, regional network, association or website has deployed, funded,
> reviewed or endorsed this project. Answers are general information, not medical advice.

## Setup

Python runs in a conda environment; packages are installed with `uv pip` (no `.venv`).
No GPU is needed: embeddings and generation use an OpenAI-compatible API, and PyTorch
(for PDF conversion) is installed as the CPU build. The conversion dependencies (docling,
trafilatura, PyTorch) are in the `ingest` extra: the backend installs the ingestion package
without them.

```bash
conda env create -f environment.yml
conda activate endorag
uv pip install -e "./ingestion[ingest,dev]" -e "./back[dev]"
cp .env.example .env   # then fill in LLM_BASE_URL and LLM_API_KEY

ruff check . && ruff format --check .
pytest

uvicorn endorag_back.routes.entrypoint:create_app --factory   # backend on :8000
```

### Frontend (chat widget and demo page)

Node 24 and npm. `front/` builds the embeddable widget (`widget.js`) and the fictional
campaign page that hosts it.

```bash
cd front
npm install
npm run mock    # optional: mock chat API on :8000 and :8001 (replayed streams, no backend needed)
npm run dev     # campaign page with the widget on http://localhost:5173
npm test && npm run build   # helper tests; dist/ with widget.js and the page
```

`?chat=open&profile=patient` opens the widget directly (the poster QR code). One backend
serves one profile, so the « Espace professionnels » entry needs a second backend
(`PROFILE=gp ... --port 8001`); the demo page's script tag already sets
`data-api-gp="http://localhost:8001"`.

## Documentation

See [docs/](docs/README.md): scenario, scope, architecture, tech stack, sources,
evaluation, local vs production, and the method used to build it.

## Source content

All documents under `data/` belong to their publishers (Haute Autorité de Santé,
Assurance Maladie, Santé.fr, EndoFrance, Service-Public, ESHRE and others listed in
[docs/sources.md](docs/sources.md)). They are included only to run this non-commercial
demonstration, with attribution and a link to the original on every answer. Publishers who
want their content removed can open an issue and it will be removed.
