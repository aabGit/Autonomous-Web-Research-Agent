from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from research_agent.graph import AGENT
from research_agent.nodes import initial_state

load_dotenv()

app = FastAPI(title="Autonomous Web Research Agent", version="0.1.0")


class ResearchRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/research")
def research(body: ResearchRequest) -> dict:
    final = AGENT.invoke(initial_state(body.question))
    return {
        "question": final["question"],
        "plan": final.get("plan"),
        "report": final.get("report"),
        "sources": list(dict.fromkeys(final.get("sources") or [])),
        "loops": final.get("loop"),
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "research_agent.api:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "8001")),
        reload=False,
    )


if __name__ == "__main__":
    main()
