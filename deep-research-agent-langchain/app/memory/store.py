from typing import List
from app.config import DISABLE_MEMORY, DISABLE_EMBEDDINGS


def build_vectorstore(docs: List[str]):
    if DISABLE_MEMORY or DISABLE_EMBEDDINGS:
        return None
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except Exception:
        return None
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    texts = [doc for doc in docs if doc.strip()]
    if not texts:
        return None
    return Chroma.from_texts(texts=texts, embedding=embeddings, persist_directory=".memory")
