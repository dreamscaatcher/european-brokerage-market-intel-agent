"""
LangGraph pipeline skeleton -- Week 1 deliverable.

Tracing: set LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY, and
LANGCHAIN_PROJECT (see .env.example) to get every run traced in LangSmith
from day one, per the portfolio's observability non-negotiable. This module
does not hardcode a tracing backend -- LangGraph picks up LangSmith env vars
automatically, and Langfuse is a drop-in alternative via its callback handler
if that's preferred instead.

Week 1 only wires the Data agent node end-to-end (fetch -> normalize).
Analyst and Briefing nodes are stubbed (see analyst_agent.py /
briefing_agent.py) and intentionally raise NotImplementedError if reached --
wiring them for real is Week 2 scope per the timeline in the project doc.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agents.data_agent import data_agent_node
from src.agents.state import BriefingState


def build_week1_graph():
    graph = StateGraph(BriefingState)
    graph.add_node("data_agent", data_agent_node)
    graph.add_edge(START, "data_agent")
    graph.add_edge("data_agent", END)
    return graph.compile()


def build_full_graph():
    """
    Target Week 2/3 shape (data -> analyst -> briefing). Left here so the
    Week 1 skeleton shows the intended final wiring, even though analyst/
    briefing nodes will raise NotImplementedError until Week 2.
    """
    from src.agents.analyst_agent import analyst_agent_node
    from src.agents.briefing_agent import briefing_agent_node

    graph = StateGraph(BriefingState)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("analyst_agent", analyst_agent_node)
    graph.add_node("briefing_agent", briefing_agent_node)
    graph.add_edge(START, "data_agent")
    graph.add_edge("data_agent", "analyst_agent")
    graph.add_edge("analyst_agent", "briefing_agent")
    graph.add_edge("briefing_agent", END)
    return graph.compile()


if __name__ == "__main__":
    app = build_week1_graph()
    result = app.invoke({})
    print(f"Fetched {len(result.get('raw_events', []))} keyword-matched events.")
