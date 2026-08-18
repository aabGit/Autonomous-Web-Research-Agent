"""GraphQL schema for the same research agent the REST route runs.

This sits next to POST /research. It is not a replacement. Interview talking
point: FastAPI can expose REST and GraphQL from one process.
"""

from __future__ import annotations

import strawberry
from strawberry.fastapi import GraphQLRouter

from research_agent.graph import AGENT
from research_agent.nodes import initial_state


@strawberry.type
class ResearchResult:
    question: str
    plan: list[str]
    report: str
    sources: list[str]
    loops: int


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> bool:
        return True


@strawberry.type
class Mutation:
    @strawberry.mutation
    def research(self, question: str) -> ResearchResult:
        final = AGENT.invoke(initial_state(question))
        return ResearchResult(
            question=final["question"],
            plan=list(final.get("plan") or []),
            report=final.get("report") or "",
            sources=list(dict.fromkeys(final.get("sources") or [])),
            loops=int(final.get("loop") or 0),
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
