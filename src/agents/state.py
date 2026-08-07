"""Shared state passed between LangGraph nodes."""

from __future__ import annotations

from typing import TypedDict


class BriefingState(TypedDict, total=False):
    # Populated by the Data agent
    raw_events: list[dict]
    fetch_errors: list[dict]

    # Populated by the Analyst agent
    new_or_changed: list[dict]  # events flagged as novel vs. prior graph state
    analysis_notes: str

    # Populated by the Briefing agent
    briefing_en: str
    briefing_de: str
    citations: list[str]  # one entry per claim in the briefing, per the
    # non-fabrication guardrail: every claim must trace to a source URL.

    # Cost/observability, filled in as the pipeline runs
    run_id: str
    cost_usd: float
