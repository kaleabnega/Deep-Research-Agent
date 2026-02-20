# Agentic AI Workspace

This repository contains:

1) `deep-research-agent-langchain` — the LangChain‑based backend research agent (FastAPI).
2) `deep-research-agent-ui` — a React + Vite frontend UI that talks to the backend.

The backend performs deep research with a Plan–Execute–Reflect loop, evidence constraints, iterative critique, and optional file ingestion. The UI provides an interface for running queries, choosing constraints, and uploading files.

---

## Project Overview

### Backend (Deep Research Agent)
- **Plan–Execute–Reflect** workflow
- Evidence constraints: source types, time range, quality
- Evidence scoring + provenance
- Critic loop with follow‑up queries
- Optional file ingestion (TXT, CSV, PDF)
- Optional long‑term memory (Chroma)
- Essay mode for long‑form synthesis

### Frontend (UI)
- React + Vite
- File upload + constraints controls
- Essay vs briefing mode
- Output panel for results

---

## Folder Structure

```
agentic-ai/
  deep-research-agent-langchain/
    app/
    requirements.txt
    README.md
  deep-research-agent-ui/
    src/
    package.json
    README.md
  README.md
```

---

## Backend Setup (FastAPI + LangChain)

### Install
```bash
cd deep-research-agent-langchain
pip install -r requirements.txt
```

### Configure `.env`
Create `.env` inside `deep-research-agent-langchain/`:
```
HF_TOKEN=your_hf_token
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2:featherless-ai
SERPAPI_API_KEY=...          # optional
TAVILY_API_KEY=...           # optional
```

### Run the API
```bash
uvicorn app.api:app --reload
```

### API Example
```bash
curl -X POST "http://127.0.0.1:8000/research" \
  -F 'question=Your research question' \
  -F 'mode=essay' \
  -F 'constraints={"source_types":["peer_reviewed"],"time_range":{"start_year":2020,"end_year":2025}}' \
  -F 'files=@/path/to/file.pdf'
```

---

## Frontend Setup (React + Vite)

### Install
```bash
cd deep-research-agent-ui
npm install
```

### Run
```bash
npm run dev
```

UI expects the backend at `http://127.0.0.1:8000`.

---

## Features in Detail

### Evidence Constraints
Constraints can be specified via the UI or API:
- `source_types`: `peer_reviewed`, `preprint`, `news`, `encyclopedia`, `blog`, `other`
- `time_range`: `start_year`, `end_year`
- `quality`: freeform flag (reserved)

The critic can also infer constraints and apply them for follow‑ups.

### Essay Mode
Essay mode generates a long‑form, cohesive response with inline citations based on structured evidence.

### File Upload
Uploaded files are ingested as evidence:
- TXT, CSV: direct text
- PDF: text extraction (requires `pypdf`)

---

