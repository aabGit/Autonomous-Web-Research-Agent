"""LangGraph wiring: nodes + edges.

ASCII map of the loop:

    START -> plan -> search -> ingest -> synthesize -> critique
                         ^                              |
                         |          gaps remain         |
                         +------------------------------+
                                        |
                                     done -> END

This is what "autonomous" means: the critique node can send the agent
back to search without you clicking anything.
"""

from langgraph.graph import END, START, StateGraph

from research_agent.nodes import (
    critique_node,
    ingest_node,
    plan_node,
    search_node,
    should_continue,
    synthesize_node,
)
from research_agent.state import ResearchState


def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("critique", critique_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "ingest")
    graph.add_edge("ingest", "synthesize")
    graph.add_edge("synthesize", "critique")
    graph.add_conditional_edges(
        "critique",
        should_continue,
        {"search": "search", "end": END},
    )
    return graph.compile()


AGENT = build_graph()
