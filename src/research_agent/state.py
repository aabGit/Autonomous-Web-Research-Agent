"""The graph's shared notebook.

LangGraph is a state machine. Every node reads this dict, does one job,
and writes back. `findings` and `sources` accumulate across loops.
"""

from __future__ import annotations

from typing import TypedDict


class Finding(TypedDict):
    query: str
    title: str
    url: str
    snippet: str
    content: str


class ResearchState(TypedDict):
    question: str
    plan: list[str]
    findings: list[Finding]
    sources: list[str]
    report: str
    gaps: list[str]
    loop: int
    done: bool
    ingested_urls: list[str]
