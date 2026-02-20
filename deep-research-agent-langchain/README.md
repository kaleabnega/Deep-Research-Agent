# Deep Research Agent (LangChain)

LangChain-based research briefing agent with plan–execute–reflect, evidence constraints, critic loop, caching, and optional file ingestion.

## Features
- LLM-driven planning and critique
- Task-driven evidence constraints (time range, source type, quality)
- Evidence scoring and provenance
- Optional file ingestion (PDF/TXT/CSV) as evidence
- Short-term conversation memory + long-term research memory (optional)

## Setup
```bash
pip install -r requirements.txt
```

## Environment
Create a `.env` file:
```
HF_TOKEN=your_hf_token_here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2:featherless-ai
SERPAPI_API_KEY=...
TAVILY_API_KEY=...
```

## Run
```bash
python main.py "Your question here"
python main.py "Question" --file ./notes.pdf --file ./data.csv
python main.py "Question" --constraints '{"source_types":["peer_reviewed"],"time_range":{"start_year":2020,"end_year":2025}}'
```

## Notes
- If `chromadb` is installed, the agent will persist long-term memory.
- If `sentence-transformers` is installed, it will use embedding-based relevance scoring.

## API
Run the server:
```bash
uvicorn app.api:app --reload
```

Example request:
```bash
curl -X POST "http://127.0.0.1:8000/research" \
  -F 'question=Your research question' \
  -F 'constraints={"source_types":["peer_reviewed"],"time_range":{"start_year":2020,"end_year":2025}}' \
  -F 'files=@/path/to/file.pdf'
```

## Essay mode
Use `mode=essay` to generate a long-form response.

Example:
```bash
curl -X POST "http://127.0.0.1:8000/research" \
  -F 'question=Your research question' \
  -F 'mode=essay'
```

## Production flags
Set these in your environment to reduce memory usage:

- `DISABLE_MEMORY=1` disables long-term vector memory.
- `DISABLE_EMBEDDINGS=1` disables embedding models.

Example:
```
DISABLE_MEMORY=1
DISABLE_EMBEDDINGS=1
```
