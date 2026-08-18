"""Pinecone integrated-index helper for research RAG.

Indexes use Pinecone-hosted embeddings (`llama-text-embed-v2` by default).
Text lives in `chunk_text` — that field name must match the index field_map.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

from research_agent.config import Settings, get_settings

TEXT_FIELD = "chunk_text"
_UPSERT_BATCH = 90


def uses_pinecone(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    mode = (settings.vector_db or "auto").strip().lower()
    if mode == "chroma":
        return False
    if mode == "pinecone":
        if not settings.pinecone_api_key:
            raise RuntimeError("VECTOR_DB=pinecone requires PINECONE_API_KEY")
        return True
    return bool(settings.pinecone_api_key)


def namespace_for(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]
    return f"ns-{digest}"


def record_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


@lru_cache
def get_index():
    from pinecone import Pinecone

    settings = get_settings()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    name = settings.pinecone_index
    if not pc.has_index(name):
        pc.create_index_for_model(
            name=name,
            cloud=settings.pinecone_cloud,
            region=settings.pinecone_region,
            embed={
                "model": settings.pinecone_embed_model,
                "field_map": {"text": TEXT_FIELD},
            },
        )
    description = pc.describe_index(name)
    host = description.host if hasattr(description, "host") else description["host"]
    return pc.Index(host=host)


def upsert_records(namespace: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    index = get_index()
    for start in range(0, len(records), _UPSERT_BATCH):
        index.upsert_records(namespace, records[start : start + _UPSERT_BATCH])


def search_text(
    namespace: str,
    query: str,
    k: int = 6,
    fields: list[str] | None = None,
    filter: dict[str, Any] | None = None,
) -> list[str]:
    payload: dict[str, Any] = {
        "inputs": {"text": query},
        "top_k": k,
    }
    if filter:
        payload["filter"] = filter
    results = get_index().search(
        namespace=namespace,
        query=payload,
        fields=fields or [TEXT_FIELD],
    )
    return _hit_texts(results)


def _hit_texts(results: Any) -> list[str]:
    if hasattr(results, "to_dict"):
        results = results.to_dict()
    hits: list[Any] = []
    if isinstance(results, dict):
        result = results.get("result") or results
        hits = result.get("hits") or results.get("hits") or []
    elif hasattr(results, "result"):
        hits = getattr(results.result, "hits", None) or []
    texts: list[str] = []
    for hit in hits:
        if hasattr(hit, "to_dict"):
            hit = hit.to_dict()
        if not isinstance(hit, dict):
            continue
        fields = hit.get("fields") or hit
        text = fields.get(TEXT_FIELD) or ""
        if text:
            texts.append(str(text))
    return texts
