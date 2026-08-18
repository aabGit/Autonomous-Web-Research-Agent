"""RAG = Retrieval Augmented Generation.

After we scrape pages, we chop them into chunks and store vectors.
Pinecone is used when PINECONE_API_KEY is set (or VECTOR_DB=pinecone).
Otherwise Chroma on disk keeps tests and offline runs working.
Later, the writer asks: "what do we already know about X?"
instead of stuffing every webpage into the prompt.
"""

from __future__ import annotations

from chromadb import PersistentClient
from chromadb.api.models.Collection import Collection

from research_agent.config import get_settings
from research_agent.pinecone_store import (
    TEXT_FIELD,
    namespace_for,
    record_id,
    search_text,
    upsert_records,
    uses_pinecone,
)


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
    chunks = chunk_text(finding.get("content") or finding.get("snippet") or "")
    if not chunks:
        return 0
    if uses_pinecone():
        return _ingest_pinecone(run_id, finding, chunks)
    return _ingest_chroma(run_id, finding, chunks)


def retrieve(question: str, run_id: str, k: int = 6) -> list[str]:
    if uses_pinecone():
        return search_text(
            namespace=namespace_for(run_id),
            query=question,
            k=k,
            fields=[TEXT_FIELD, "url", "title"],
            filter={"run_id": {"$eq": run_id}},
        )
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


def _ingest_chroma(run_id: str, finding: dict, chunks: list[str]) -> int:
    collection = get_collection()
    ids = []
    documents = []
    metadatas = []
    url = finding["url"]
    for index, chunk in enumerate(chunks):
        ids.append(record_id(run_id, url, str(index)))
        documents.append(chunk)
        metadatas.append(
            {
                "url": url,
                "title": finding.get("title") or "",
                "query": finding.get("query") or "",
                "run_id": run_id,
            }
        )
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(documents)


def _ingest_pinecone(run_id: str, finding: dict, chunks: list[str]) -> int:
    url = finding["url"]
    records = []
    for index, chunk in enumerate(chunks):
        records.append(
            {
                "_id": record_id(run_id, url, str(index)),
                TEXT_FIELD: chunk[:8000],
                "url": url[:500],
                "title": (finding.get("title") or "")[:500],
                "query": (finding.get("query") or "")[:500],
                "run_id": run_id[:500],
            }
        )
    upsert_records(namespace_for(run_id), records)
    return len(records)
