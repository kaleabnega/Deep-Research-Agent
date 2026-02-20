from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
import tempfile
from pathlib import Path

from app.agents.research_agent import DeepResearchAgent

app = FastAPI(title="Deep Research Agent")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/research")
async def research(
    question: str = Form(...),
    mode: str = Form("briefing"),
    constraints: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
):
    agent = DeepResearchAgent()
    file_paths = []
    try:
        for f in files:
            suffix = Path(f.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await f.read()
                tmp.write(content)
                file_paths.append(tmp.name)
        parsed_constraints = json.loads(constraints) if constraints else None
        report = agent.run(question=question, file_paths=file_paths, constraints=parsed_constraints, mode=mode)
        return JSONResponse({"report": report})
    finally:
        for p in file_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
