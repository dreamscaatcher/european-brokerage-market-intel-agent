"""
LangGraph pipeline -- Week 1 wired the Data agent alone; Week 2 wires the
full Data -> Analyst -> Briefing chain for real.

Tracing: set LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY, and
LANGCHAIN_PROJECT (see .env.example) to get every run traced in LangSmith
from day one, per the portfolio's observability non-negotiable. This module
does not hardcode a tracing backend -- LangGraph picks up LangSmith env vars
automatically, and Langfuse is a drop-in alternative via its callback handler
if that's preferred instead. Not yet live-verified in LangSmith itself --
needs a real LANGCHAIN_API_KEY, same gate as the Briefing agent's
ANTHROPIC_API_KEY.

build_full_graph() will raise RuntimeError at the briefing_agent step if
ANTHROPIC_API_KEY isn't set -- intentional (see briefing_agent.py), not a bug.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agents.data_agent import data_agent_node
from src.agents.state import BriefingState


def build_week1_graph():
    """Fetch + upsert only, no LLM involved. Still useful on its own for a
    cheap 'just refresh the graph' run without generating a briefing."""
    graph = StateGraph(BriefingState)
    graph.add_node("data_agent", data_agent_node)
    graph.add_edge(START, "data_agent")
    graph.add_edge("data_agent", END)
    return graph.compile()


def build_full_graph():
    """Data -> Analyst -> Briefing, end-to-end. Analyst has no LLM
    dependency and is fully live-tested against the Aura graph. Briefing
    needs ANTHROPIC_API_KEY."""
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
    import os
    import sys

    if "--full" in sys.argv and os.environ.get("ANTHROPIC_API_KEY"):
        app = build_full_graph()
        result = app.invoke({})
        print(f"Briefing (EN):\n{result['briefing_en']}\n")
        print(f"cost_usd={result['cost_usd']}")
    else:
        app = build_week1_graph()
        result = app.invoke({})
        print(f"Fetched + upserted {len(result.get('raw_events', []))} keyword-matched events.")
