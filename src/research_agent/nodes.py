from __future__ import annotations

import json
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import get_settings
from research_agent.llm import get_chat_model
from research_agent.rag import ingest_finding, retrieve
from research_agent.state import Finding, ResearchState
from research_agent.tools import fetch_url, web_search


PLAN_PROMPT = """You are a research planner.
Break the user's question into 3-5 focused web search queries.
Return JSON only: {"queries": ["...", "..."]}
"""

SYNTH_PROMPT = """You are a careful research writer.
Use ONLY the retrieved notes. Cite URLs inline like (https://...).
If something is unknown, say so. Write markdown with:
- Executive summary
- Key findings
- Open questions
"""

CRITIQUE_PROMPT = """You are a skeptical editor.
Given the original question and the draft report, list missing facts.
Return JSON only: {"done": true/false, "gaps": ["..."]}
Set done=true if the report reasonably answers the question.
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
    return {"plan": queries[:5], "loop": state.get("loop", 0)}


def search_node(state: ResearchState) -> dict:
    queries = state.get("gaps") or state.get("plan") or [state["question"]]
    findings: list[Finding] = list(state.get("findings") or [])
    sources = list(state.get("sources") or [])
    seen = {item["url"] for item in findings}

    for query in queries[:4]:
        for hit in web_search(query):
            url = hit["url"]
            if not url or url in seen:
                continue
            seen.add(url)
            try:
                content = fetch_url(url)
            except Exception:
                content = hit.get("snippet") or ""
            finding: Finding = {
                "query": query,
                "title": hit.get("title") or url,
                "url": url,
                "snippet": hit.get("snippet") or "",
                "content": content,
            }
            findings.append(finding)
            sources.append(url)

    return {"findings": findings, "sources": sources}


def ingest_node(state: ResearchState) -> dict:
    run_id = state.get("question", "")[:80]
    for finding in state.get("findings") or []:
        ingest_finding(run_id, finding)
    return {}


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
    }


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]
