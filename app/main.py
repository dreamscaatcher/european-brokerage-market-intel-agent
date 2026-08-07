"""
FastAPI backend for the deployed app -- Week 3 deliverable
("Deployed app: chat interface, daily-refresh briefing, EN/DE toggle").

Reuses the exact same logic as the MCP server tools (src/mcp_server/server.py)
and the pipeline (src/agents/pipeline.py) rather than re-implementing graph
queries -- one source of truth for "what a competitor lookup returns" whether
you're asking through Claude Desktop or this web UI.

Run locally:
    uvicorn app.main:app --reload
Deploy: see Dockerfile / Procfile at repo root. Needs the same .env as the
rest of the project (NEO4J_*, ANTHROPIC_API_KEY) set as environment
variables on whatever host runs it.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.agents.pipeline import build_full_graph
from src.graph.loader import get_latest_briefing
from src.mcp_server.server import get_regulatory_updates as _get_regulatory_updates
from src.mcp_server.server import query_competitor as _query_competitor

app = FastAPI(title="European Brokerage Market Intelligence Agent")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _unwrap(tool):
    """MCP tools are decorated; call the underlying function directly."""
    return getattr(tool, "fn", tool)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/briefing")
def api_get_briefing(language: str = "en"):
    lang = "de" if language.lower().startswith("de") else "en"
    briefing = get_latest_briefing(lang)
    if not briefing:
        return {"exists": False, "message": "No briefing generated yet."}
    return {"exists": True, **briefing}


@app.post("/api/briefing/refresh")
def api_refresh_briefing():
    """
    Runs the full pipeline (Data -> Analyst -> Briefing) right now. This
    calls the live feeds and the Anthropic API -- it costs real money
    (~$0.01-0.02 per the measured figures in eval/results_2026-08-07.md) and
    is NOT free to spam. A real deployment should gate this behind auth
    and/or a daily cron rather than leaving it open to any caller -- flagged
    here rather than silently shipped as-is.
    """
    try:
        app_graph = build_full_graph()
        result = app_graph.invoke({})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "run_id": result.get("run_id"),
        "cost_usd": result.get("cost_usd"),
        "events_covered": len(result.get("new_or_changed", [])),
    }


@app.get("/api/competitor/{company_name}")
def api_query_competitor(company_name: str):
    return {"result": _unwrap(_query_competitor)(company_name)}


@app.get("/api/regulatory")
def api_get_regulatory_updates(days: int = 7):
    return {"result": _unwrap(_get_regulatory_updates)(days)}


@app.get("/api/health")
def health():
    return {"status": "ok"}
