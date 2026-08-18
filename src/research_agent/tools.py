"""Web tools used both by LangGraph nodes and by the MCP server.

MCP (Model Context Protocol) is a standard way to expose tools to any
LLM host. We keep the real work here so MCP is just a thin wrapper.
"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

from research_agent.config import get_settings


def web_search(query: str, max_results: int | None = None) -> list[dict]:
    settings = get_settings()
    limit = max_results or settings.search_results_per_query

    if settings.tavily_api_key:
        return _tavily_search(query, limit, settings.tavily_api_key)

    rows: list[dict] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=limit):
            rows.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("href") or item.get("url") or "",
                    "snippet": item.get("body") or "",
                }
            )
    return rows


def _tavily_search(query: str, limit: int, api_key: str) -> list[dict]:
    response = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": limit},
        timeout=30.0,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return [
        {
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "snippet": item.get("content") or "",
        }
        for item in results
    ]


def fetch_url(url: str) -> str:
    settings = get_settings()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/0.1)"}
    with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n"))
    return text.strip()[: settings.max_page_chars]
