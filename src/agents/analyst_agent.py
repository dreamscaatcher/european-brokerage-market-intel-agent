"""
Analyst agent -- Week 2.

Reasons over the live Neo4j graph (not the raw feed pull) to find events not
yet covered by a briefing, and applies the project's non-fabrication
guardrail: something only gets called a "trend" if at least 2 independent
sources report on the same tracked company. Everything else is real signal,
but must be described as single-sourced, not a trend.

Deliberately no LLM call in this module -- the trend/no-trend determination
is a deterministic fact about the graph (how many distinct Source nodes
point at a Company via an Event), not something to leave to a language
model's judgment. The Briefing agent is downstream and is instructed to
respect whatever this module decides; it doesn't get to override it.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.agents.state import BriefingState
from src.graph.loader import DATABASE, get_driver

UNBRIEFED_EVENTS_QUERY = """
MATCH (e:Event)
WHERE e.briefed_at IS NULL
OPTIONAL MATCH (e)-[:MENTIONS]->(c:Company)
OPTIONAL MATCH (e)-[:FROM_SOURCE]->(s:Source)
RETURN e.event_id AS event_id, e.title AS title, e.link AS link,
       e.published AS published, e.summary AS summary, e.category AS category,
       collect(DISTINCT c.name) AS companies, s.source_id AS source_id,
       s.name AS source_name
"""


def _fetch_unbriefed_events() -> list[dict[str, Any]]:
    driver = get_driver()
    try:
        with driver.session(database=DATABASE) as session:
            return [dict(record) for record in session.run(UNBRIEFED_EVENTS_QUERY)]
    finally:
        driver.close()


def _flag_trends(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    """A company is 'trending' this run only if >=2 distinct Source nodes
    have an Event mentioning it. Single-company/single-source events are
    real but not trends -- the guardrail the Briefing agent must respect."""
    company_sources: dict[str, set[str]] = defaultdict(set)
    for event in events:
        for company in event["companies"]:
            if company:
                company_sources[company].add(event["source_id"])

    trending_companies = {c for c, sources in company_sources.items() if len(sources) >= 2}

    annotated = []
    for event in events:
        companies = [c for c in event["companies"] if c]
        is_trend = any(c in trending_companies for c in companies)
        annotated.append(
            {
                **event,
                "companies": companies,
                "is_trend": is_trend,
                "supporting_source_count": (
                    len(company_sources[companies[0]]) if companies else 1
                ),
            }
        )
    return annotated, trending_companies


def analyst_agent_node(state: BriefingState) -> BriefingState:
    events = _fetch_unbriefed_events()
    annotated, trending_companies = _flag_trends(events)

    notes = [f"{len(annotated)} un-briefed event(s) since the last run."]
    if trending_companies:
        notes.append(
            "Trend flagged (>=2 independent sources): " + ", ".join(sorted(trending_companies)) + "."
        )
    else:
        notes.append(
            "No cross-source trends this run -- every event is single-sourced. "
            "Per the non-fabrication guardrail, none of today's items may be "
            "described as a 'trend' in the briefing."
        )

    return {
        **state,
        "new_or_changed": annotated,
        "analysis_notes": "\n".join(notes),
    }


if __name__ == "__main__":
    result = analyst_agent_node({})
    print(result["analysis_notes"])
    print(f"\n{len(result['new_or_changed'])} events ready for the Briefing agent.")
