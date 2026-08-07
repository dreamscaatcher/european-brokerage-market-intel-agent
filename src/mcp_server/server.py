"""
MCP server -- Week 2 ("core deliverable, not optional" per the scope doc).

get_daily_briefing needs a Briefing node to exist (i.e. a full pipeline run
with ANTHROPIC_API_KEY set) -- returns a plain "no briefing yet" message
rather than an error if none exists, since that's an expected, valid state
early on, not a failure.

query_competitor and get_regulatory_updates are pure graph reads with no
LLM dependency -- both are live-tested against the Aura instance as of
2026-08-07.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

# The mcp SDK renamed FastMCP -> MCPServer as of v2.0.0 (mcp.server.fastmcp no
# longer exists; found this the hard way when the old import 404'd on import).
# Same decorator-based .tool() API, just a new home and name.
from mcp.server.mcpserver import MCPServer

from src.graph.loader import DATABASE, get_driver, get_latest_briefing

mcp = MCPServer("european-brokerage-market-intel")

REGULATOR_SOURCE_IDS = ["bafin_all_news", "esma_news"]


@mcp.tool()
def get_daily_briefing(language: str = "en") -> str:
    """Return the latest daily SITREP in English ('en') or German ('de')."""
    lang = "de" if language.lower().startswith("de") else "en"
    briefing = get_latest_briefing(lang)
    if not briefing:
        return (
            "No briefing has been generated yet. Run the full pipeline "
            "(python -m src.agents.pipeline --full) with ANTHROPIC_API_KEY "
            "set to produce the first one."
        )
    return (
        f"Briefing {briefing['briefing_id']} ({briefing['date']}, "
        f"cost ${briefing['cost_usd']:.4f}):\n\n{briefing['text']}"
    )


@mcp.tool()
def query_competitor(company_name: str) -> str:
    """Graph-backed lookup on a tracked company: recent events mentioning it."""
    driver = get_driver()
    try:
        with driver.session(database=DATABASE) as session:
            rows = [
                dict(r)
                for r in session.run(
                    """
                    MATCH (c:Company)
                    WHERE toLower(c.name) = toLower($name)
                    OPTIONAL MATCH (c)<-[:MENTIONS]-(e:Event)-[:FROM_SOURCE]->(s:Source)
                    RETURN c.name AS company, e.title AS title, e.link AS link,
                           e.published AS published, s.name AS source
                    ORDER BY e.published DESC
                    LIMIT 10
                    """,
                    name=company_name,
                )
            ]
    finally:
        driver.close()

    if not rows:
        return f"'{company_name}' is not a tracked company."
    if rows[0]["title"] is None:
        return f"'{rows[0]['company']}' is tracked but has no linked events yet."

    canonical_name = rows[0]["company"]
    lines = [f"Recent tracked events for {canonical_name}:"]
    for row in rows:
        lines.append(f"- {row['title']} (source: {row['source']}, link: {row['link']})")
    return "\n".join(lines)


@mcp.tool()
def get_regulatory_updates(days: int = 7) -> str:
    """Recent BaFin/ESMA items from the last N days (falls back to including
    items whose publish date can't be parsed, rather than silently dropping
    them -- inclusion on a parse failure is the safe default here, not a
    fabrication risk, since the item itself is real)."""
    driver = get_driver()
    try:
        with driver.session(database=DATABASE) as session:
            rows = [
                dict(r)
                for r in session.run(
                    """
                    MATCH (e:Event)-[:FROM_SOURCE]->(s:Source)
                    WHERE s.source_id IN $source_ids
                    RETURN e.title AS title, e.link AS link,
                           e.published AS published, s.name AS source
                    ORDER BY e.published DESC
                    LIMIT 50
                    """,
                    source_ids=REGULATOR_SOURCE_IDS,
                )
            ]
    finally:
        driver.close()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for row in rows:
        try:
            published = date_parser.parse(row["published"])
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published >= cutoff:
                recent.append(row)
        except (TypeError, ValueError):
            recent.append(row)  # can't parse the date -- include rather than drop

    if not recent:
        return f"No BaFin/ESMA items found in the last {days} day(s)."

    lines = [f"Regulatory updates (last {days} day(s)):"]
    for row in recent:
        lines.append(f"- [{row['source']}] {row['title']} (link: {row['link']})")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
