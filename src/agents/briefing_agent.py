"""
Briefing agent -- STUB, Week 2 work per the timeline.

Will produce the daily SITREP (situation / assessment / recommendation) in
plain business English, plus a German-language toggle. Every claim must
carry a citation back to a src/graph Event node's source link -- this is
where the non-fabrication guardrail gets enforced structurally, not just
by prompting.
"""

from __future__ import annotations

from src.agents.state import BriefingState


def briefing_agent_node(state: BriefingState) -> BriefingState:
    raise NotImplementedError(
        "Briefing agent is Week 2 scope. Week 1 deliverable is the Data agent "
        "+ populated graph schema; see README.md roadmap."
    )
