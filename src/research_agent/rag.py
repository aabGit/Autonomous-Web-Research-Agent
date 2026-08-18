"""RAG = Retrieval Augmented Generation.

After we scrape pages, we chop them into chunks and store vectors in
Chroma. Later, the writer asks Chroma: "what do we already know about X?"
instead of stuffing every webpage into the prompt.
"""

from __future__ import annotations

from chromadb import PersistentClient
from chromadb.api.models.Collection import Collection

from research_agent.config import get_settings


def get_collection() -> Collection:
    settings = get_settings()
    client = PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(name=settings.chroma_collection)


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        piece = words[start : start + size]
        if piece:
            chunks.append(" ".join(piece))
        start += size - overlap
    return chunks or [text]


def ingest_finding(run_id: str, finding: dict) -> int:
    collection = get_collection()
    chunks = chunk_text(finding.get("content") or finding.get("snippet") or "")
    ids = []
    documents = []
    metadatas = []
    safe_url = str(abs(hash(finding["url"])))
    safe_run = str(abs(hash(run_id)))
    for index, chunk in enumerate(chunks):
        ids.append(f"{safe_run}-{safe_url}-{index}")
        documents.append(chunk)
        metadatas.append(
            {
                "url": finding["url"],
                "title": finding.get("title") or "",
                "query": finding.get("query") or "",
                "run_id": run_id,
            }
        )
    if documents:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(documents)


def retrieve(question: str, run_id: str, k: int = 6) -> list[str]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_texts=[question],
        n_results=min(k, collection.count()),
        where={"run_id": run_id},
    )
    documents = result.get("documents") or [[]]
    return documents[0]
