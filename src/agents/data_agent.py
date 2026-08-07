"""
Data agent -- LangGraph node wrapping the ingestion module.

Week 1 scope: this node just runs the deterministic feed pull and hands
normalized events to the rest of the graph. No LLM call happens here on
purpose -- keeping ingestion LLM-free keeps it cheap, testable, and immune
to hallucination before anything reaches the Analyst agent.
"""

from __future__ import annotations

from src.agents.state import BriefingState
from src.ingestion.feeds import pull_all_events


def data_agent_node(state: BriefingState, config_path: str = "config/sources.yaml") -> BriefingState:
    events = pull_all_events(config_path)
    return {
        **state,
        "raw_events": [e.to_dict() for e in events],
        "fetch_errors": [],  # pull_all_events currently logs errors to stdout;
        # Week 2 TODO: return them structured instead of just printing, so the
        # Briefing agent can flag "N sources unreachable today" in the SITREP
        # rather than silently under-reporting.
    }
