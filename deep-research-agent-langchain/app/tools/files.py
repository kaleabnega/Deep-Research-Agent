from pathlib import Path
from typing import List, Dict


def ingest_files(paths: List[str]) -> List[Dict[str, str]]:
    docs = []
    for path in paths:
        file_path = Path(path)
        if not file_path.exists():
            continue
        if file_path.suffix.lower() == ".txt":
            docs.append({"title": file_path.name, "content": file_path.read_text(errors="ignore")})
        elif file_path.suffix.lower() == ".csv":
            docs.append({"title": file_path.name, "content": file_path.read_text(errors="ignore")})
        elif file_path.suffix.lower() == ".pdf":
            text = _read_pdf(file_path)
            docs.append({"title": file_path.name, "content": text})
    return docs


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(chunks)
