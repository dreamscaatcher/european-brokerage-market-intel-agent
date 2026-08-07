"""
Analyst agent -- STUB, Week 2 work per the timeline.

Will reason over the Neo4j graph (companies / partnerships / regulators /
events) to flag what's new or changed since the last run, using the graph
built in src/graph/loader.py as the retrieval layer. Deliberately not
implemented yet: the doc's anti-drift rule is that each week ends with
something demoable, and per-week scope shouldn't bleed into the next.
"""

from __future__ import annotations

from src.agents.state import BriefingState


def analyst_agent_node(state: BriefingState) -> BriefingState:
    raise NotImplementedError(
        "Analyst agent is Week 2 scope. Week 1 deliverable is the Data agent "
        "+ populated graph schema; see README.md roadmap."
    )
