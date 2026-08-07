"""
Data agent -- LangGraph node wrapping the ingestion module.

Week 1 shipped fetch+normalize only, with graph writes as a separate manual
CLI step (`loader.py ingest`). Week 2 closes that gap: this node now also
upserts into Neo4j so the full pipeline (Data -> Analyst -> Briefing) is
genuinely end-to-end -- the Analyst agent reads live graph state that THIS
run just wrote, not whatever was left over from the last manual `ingest`.

Still no LLM call here on purpose -- keeping ingestion LLM-free keeps it
cheap, testable, and immune to hallucination before anything reaches the
Analyst agent.
"""

from __future__ import annotations

import yaml

from src.agents.state import BriefingState
from src.graph.loader import upsert_events
from src.ingestion.feeds import pull_all_events


def data_agent_node(state: BriefingState, config_path: str = "config/sources.yaml") -> BriefingState:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    tracked_companies = config.get("tracked_companies", [])

    events = pull_all_events(config_path)
    written = upsert_events(events, tracked_companies)
    print(f"[data_agent] upserted {written} events into the graph.")

    return {
        **state,
        "raw_events": [e.to_dict() for e in events],
        "fetch_errors": [],  # pull_all_events currently logs errors to stdout;
        # TODO: return them structured instead of just printing, so the
        # Briefing agent can flag "N sources unreachable today" in the SITREP
        # rather than silently under-reporting.
    }
