from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import get_settings
from research_agent.llm import get_chat_model
from research_agent.rag import ingest_finding, retrieve
from research_agent.state import Finding, ResearchState
from research_agent.tools import fetch_url, web_search


# Prompt style: few-shot examples + function-style JSON (the model must
# return this object the way a tool/function call would).
PLAN_PROMPT = """You are a research planner.
Break the user's question into 2-3 focused web search queries.

Examples of good output:

Question: What is LangGraph?
{"queries": ["LangGraph official docs", "LangGraph vs LangChain agents", "LangGraph state and checkpointing"]}

Question: How does RAG reduce hallucinations?
{"queries": ["retrieval augmented generation overview", "RAG hallucination reduction", "vector database RAG best practices"]}

Return JSON only in this shape:
{"queries": ["...", "..."]}
"""

# Prompt style: zero-shot — instructions only, no examples.
SYNTH_PROMPT = """You are a careful research writer.
Use ONLY the retrieved notes. Cite URLs inline like (https://...).
If something is unknown, say so. Write markdown with:
- Executive summary
- Key findings
- Open questions
"""

# Prompt style: chain-of-thought, then function-style JSON.
CRITIQUE_PROMPT = """You are a skeptical editor.
Think step by step before you answer:
1. What did the user actually ask?
2. Which claims in the draft have sources?
3. What important facts are still missing?

Then return JSON only:
{"done": true/false, "gaps": ["missing search query", "..."]}

Set done=true if the report reasonably answers the question.
Keep the reasoning above the JSON. Do not put the reasoning inside the JSON.
"""


def _json_from_model(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {}
    return json.loads(text[start : end + 1])


def plan_node(state: ResearchState) -> dict:
    model = get_chat_model(temperature=0)
    response = model.invoke(
        [
            SystemMessage(content=PLAN_PROMPT),
            HumanMessage(content=state["question"]),
        ]
    )
    payload = _json_from_model(str(response.content))
    queries = payload.get("queries") or [state["question"]]
    return {"plan": queries[:3], "loop": state.get("loop", 0)}


def search_node(state: ResearchState) -> dict:
    settings = get_settings()
    queries = state.get("gaps") or state.get("plan") or [state["question"]]
    findings: list[Finding] = list(state.get("findings") or [])
    sources = list(state.get("sources") or [])
    seen = {item["url"] for item in findings}
    pending: list[tuple[str, dict]] = []

    for query in queries[:3]:
        for hit in web_search(query):
            url = hit["url"]
            if not url or url in seen:
                continue
            seen.add(url)
            pending.append((query, hit))
            if len(pending) >= settings.max_pages_per_run:
                break
        if len(pending) >= settings.max_pages_per_run:
            break

    def _fetch_one(item: tuple[str, dict]) -> Finding:
        query, hit = item
        url = hit["url"]
        try:
            content = fetch_url(url)
        except Exception:
            content = hit.get("snippet") or ""
        return {
            "query": query,
            "title": hit.get("title") or url,
            "url": url,
            "snippet": hit.get("snippet") or "",
            "content": content,
        }

    if pending:
        with ThreadPoolExecutor(max_workers=min(4, len(pending))) as pool:
            fetched = list(pool.map(_fetch_one, pending))
        findings.extend(fetched)
        sources.extend(item["url"] for item in fetched)

    return {"findings": findings, "sources": sources}


def ingest_node(state: ResearchState) -> dict:
    run_id = state.get("question", "")[:80]
    ingested = list(state.get("ingested_urls") or [])
    seen = set(ingested)
    for finding in state.get("findings") or []:
        url = finding["url"]
        if url in seen:
            continue
        ingest_finding(run_id, finding)
        seen.add(url)
        ingested.append(url)
    return {"ingested_urls": ingested}


def synthesize_node(state: ResearchState) -> dict:
    notes = retrieve(state["question"], run_id=state["question"][:80])
    if not notes:
        notes = [
            f"{item['title']} ({item['url']}): {item['snippet']}"
            for item in state.get("findings") or []
        ]
    model = get_chat_model(temperature=0.2)
    packed = "\n\n".join(notes[:8]) or "No notes retrieved."
    response = model.invoke(
        [
            SystemMessage(content=SYNTH_PROMPT),
            HumanMessage(
                content=f"Question:\n{state['question']}\n\nNotes:\n{packed}"
            ),
        ]
    )
    return {"report": str(response.content)}


def critique_node(state: ResearchState) -> dict:
    settings = get_settings()
    model = get_chat_model(temperature=0)
    response = model.invoke(
        [
            SystemMessage(content=CRITIQUE_PROMPT),
            HumanMessage(
                content=(
                    f"Question:\n{state['question']}\n\n"
                    f"Report:\n{state.get('report', '')}"
                )
            ),
        ]
    )
    payload = _json_from_model(str(response.content))
    loop = int(state.get("loop") or 0) + 1
    gaps = payload.get("gaps") or []
    done = bool(payload.get("done", False)) or loop >= settings.max_research_loops
    return {"gaps": gaps, "done": done, "loop": loop}


def should_continue(state: ResearchState) -> str:
    return "end" if state.get("done") else "search"


def initial_state(question: str) -> ResearchState:
    return {
        "question": question,
        "plan": [],
        "findings": [],
        "sources": [],
        "report": "",
        "gaps": [],
        "loop": 0,
        "done": False,
        "ingested_urls": [],
    }


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]
