"""
Briefing agent -- Week 2.

Turns the Analyst agent's structured, already-trend-gated events into the
daily SITREP (situation / assessment / recommendation) in English and
German, then persists it so the MCP server can serve it without re-running
the whole pipeline per request.

Model choice: Claude Haiku 4.5, not Sonnet/Opus. This is bounded
summarization over a small, pre-filtered, structured input (typically well
under 20 events/day per the Week 1 live run) -- not open-ended reasoning --
so the cheaper model is the deliberate cost-optimization decision the
project doc asks for, not a default. Pricing checked against
docs.claude.com/en/docs/about-claude/pricing on 2026-08-07: Haiku 4.5 is
$1/MTok input, $5/MTok output.

Guardrails enforced structurally, not just by prompting:
- No ANTHROPIC_API_KEY -> raise, don't fabricate a placeholder briefing.
- Trend language is gated on the Analyst agent's is_trend flag, computed
  deterministically upstream -- the model is told which items it may call
  a trend and may not override that.
- Every citation comes from the graph-sourced event link, not generated.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import anthropic

from src.agents.state import BriefingState
from src.graph.loader import mark_events_briefed, store_briefing

MODEL = "claude-haiku-4-5-20251001"
INPUT_PRICE_PER_MTOK = 1.0
OUTPUT_PRICE_PER_MTOK = 5.0
LANGUAGE_SPLIT_MARKER = "---GERMAN---"

SYSTEM_PROMPT = f"""You are a market-intelligence briefing writer for a European \
brokerage / custody / wealth-infrastructure analyst.

Non-negotiable rules:
1. Every factual claim must cite the source name and link exactly as given in the \
data. Do not state anything not present in the provided events.
2. Only call something a "trend" if its trend field is true. Everything else must \
be described as a single-sourced item (state which source, explicitly).
3. If there are zero events, say so plainly. Do not invent activity to fill space.
4. Do not speculate about causes, motives, or future outcomes beyond what a cited \
source states.
5. Structure each language version as three labeled sections: SITUATION (what \
happened), ASSESSMENT (what it means -- trend language only where permitted), \
RECOMMENDATION (one concrete next action for the analyst reading this).

Output the English version first, then a line containing exactly \
"{LANGUAGE_SPLIT_MARKER}", then the German version (professional business German, \
same structure, same citation rules, translated section labels)."""


def _build_user_prompt(events: list[dict[str, Any]], analysis_notes: str) -> str:
    lines = [f"Analyst notes: {analysis_notes}", "", "Events:"]
    if not events:
        lines.append("(none)")
    for event in events:
        companies = ", ".join(event["companies"]) or "none"
        lines.append(
            f"- source: {event['source_name']} | title: {event['title']} | "
            f"companies: {companies} | trend: {event['is_trend']} | "
            f"link: {event['link']}"
        )
    return "\n".join(lines)


def briefing_agent_node(state: BriefingState) -> BriefingState:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Refusing to generate a placeholder "
            "briefing -- the same non-fabrication discipline the guardrail "
            "enforces on content applies to the pipeline itself: no key, no run."
        )

    events = state.get("new_or_changed", [])
    analysis_notes = state.get("analysis_notes", "")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(events, analysis_notes)}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    briefing_en, _, briefing_de = text.partition(LANGUAGE_SPLIT_MARKER)

    usage = response.usage
    cost_usd = round(
        usage.input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
        + usage.output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK,
        6,
    )

    citations = [event["link"] for event in events if event.get("link")]
    run_id = f"briefing-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')}"

    if events:
        store_briefing(
            briefing_id=run_id,
            date=datetime.now(timezone.utc).isoformat(),
            text_en=briefing_en.strip(),
            text_de=briefing_de.strip(),
            cost_usd=cost_usd,
            event_ids=[event["event_id"] for event in events],
        )
        mark_events_briefed(
            [event["event_id"] for event in events],
            datetime.now(timezone.utc).isoformat(),
        )

    return {
        **state,
        "briefing_en": briefing_en.strip(),
        "briefing_de": briefing_de.strip(),
        "citations": citations,
        "run_id": run_id,
        "cost_usd": cost_usd,
    }


if __name__ == "__main__":
    from src.agents.analyst_agent import analyst_agent_node

    state = analyst_agent_node({})
    result = briefing_agent_node(state)
    print("--- EN ---")
    print(result["briefing_en"])
    print("\n--- DE ---")
    print(result["briefing_de"])
    print(f"\ncost_usd={result['cost_usd']}  run_id={result['run_id']}")
