"""
MCP server -- STUB, Week 2 deliverable per the project doc ("core deliverable,
not optional"). Sketched here now so the three tool signatures are locked in
early and the rest of the pipeline can be built against them.

Tools (per scope doc):
    get_daily_briefing(language: "en" | "de") -> latest SITREP
    query_competitor(company_name: str) -> graph-backed lookup
    get_regulatory_updates(days: int = 7) -> recent BaFin/ESMA items

Not implemented yet -- needs the Analyst/Briefing agents (Week 2) and a
populated graph to query against.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("european-brokerage-market-intel")


@mcp.tool()
def get_daily_briefing(language: str = "en") -> str:
    """Return the latest daily SITREP in English or German."""
    raise NotImplementedError("Week 2 deliverable -- needs Briefing agent.")


@mcp.tool()
def query_competitor(company_name: str) -> str:
    """Graph-backed lookup on a tracked company (partnerships, recent events)."""
    raise NotImplementedError("Week 2 deliverable -- needs populated graph + Analyst agent.")


@mcp.tool()
def get_regulatory_updates(days: int = 7) -> str:
    """Recent BaFin/ESMA regulatory items from the last N days."""
    raise NotImplementedError("Week 2 deliverable -- needs populated graph.")


if __name__ == "__main__":
    mcp.run()
