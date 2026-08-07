# European Brokerage Market Intelligence Agent

Daily "market SITREP" agent over the European brokerage / custody / investment-
infrastructure space: competitor moves, funding rounds, partnerships, and
regulatory developments (BaFin/ESMA). Built for the lemon.markets Founder's
Associate application; stands on its own as a portfolio flagship regardless
of that outcome.

Full scope, rationale, eval method, and timeline: see the project scope doc.
This README tracks build status against that plan.

## Status: Week 1 closed, Week 2 built and mostly live-verified (2026-08-07)

Per the doc's own risk assessment, data acquisition is the riskiest part of
this project. So Week 1 focused entirely on de-risking that before touching
anything else.

**Done and live-verified today:**

- Found and tested real v1 feed URLs (not assumed from docs) for all four
  committed sources. Two return valid RSS/XML from a plain fetch; Fintech
  Futures returns HTTP 403 (Cloudflare bot challenge) and was dropped from
  v1 rather than fought with a scraper workaround -- the doc's "2-3 fintech
  feeds" commitment is already met by the two that work.
- `src/ingestion/feeds.py` fetches all four feeds, normalizes entries into a
  common `RawEvent` schema, and filters by a keyword list scoped to
  brokerage/custody/wealth-infrastructure relevance.
- 4/4 live tests pass in `tests/test_ingestion.py` against the real feeds
  (not mocked) -- see the test file for why that's the point.
- Found and fixed a real filtering bug during today's live run: "BaFin" and
  "ESMA" were in the generic keyword list, so every item from those feeds
  trivially matched on the source's own name. First live run: 20/20 BaFin
  matches, 19 of them generic consumer-scam warnings. After pulling the
  regulator names out of the keyword list: 7 BaFin matches, all touching
  actual investment-services/securities content. Total keyword-matched
  events across all four feeds: 18 (was 33 before the fix).
- LangGraph pipeline skeleton (`src/agents/pipeline.py`) wires the Data agent
  node end-to-end; `build_full_graph()` shows the intended Week 2/3 wiring
  (Analyst, Briefing) with those nodes stubbed to raise `NotImplementedError`
  on purpose, so the skeleton can't silently pretend to do more than it does.
- Neo4j schema deployed and populated on a dedicated Aura Free instance
  (`european-brokerage-market-intel`, separate from the portfolio-tracking
  graph): `python -m src.graph.loader init` applied constraints/indexes +
  seed data, `... ingest` upserted the live pull. Independently verified with
  a read query, not just "no errors on write": 18 Events, 5 Companies (all
  seeded), 2 Regulators, 4 Sources, and at least one real `MENTIONS` edge
  (the Payment & Banking piece on Trade Republic's SpaceX-IPO marketing
  correctly links `Event -> MENTIONS -> Trade Republic`).
- Sample live output: `data/sample_run_2026-08-07.json` (18 real matched
  events from today's run).

Week 1 closed out same day: repo pushed to
[github.com/dreamscaatcher/european-brokerage-market-intel-agent](https://github.com/dreamscaatcher/european-brokerage-market-intel-agent)
(verified live via the public GitHub API), Aura graph populated and confirmed.

**Week 2, built 2026-08-07:**

- `src/agents/analyst_agent.py`: real implementation, no stub, no LLM call.
  Queries the live graph for events with `briefed_at IS NULL`, and applies
  the guardrail deterministically -- a company only gets called a "trend" if
  >=2 distinct Source nodes report on it. Live-verified against Aura: with
  today's 18 events (1 company mention, from 1 source), it correctly reports
  zero trends and flags all 18 as single-sourced. No LLM needed for this to
  be true or testable.
- `src/agents/briefing_agent.py`: real implementation using Claude Haiku 4.5
  (chosen over Sonnet/Opus as the cost-optimization decision the doc asks
  for -- this is bounded summarization over a small structured input, not
  open-ended reasoning; pricing confirmed against docs.claude.com on
  2026-08-07: $1/$5 per MTok in/out). Enforces citations and the trend
  guardrail via the system prompt, and via data: the Analyst agent's
  `is_trend` flag is computed upstream, not left to the model's judgment.
  **Blocked on `ANTHROPIC_API_KEY`** -- verified the block itself works:
  running it with no key raises `RuntimeError` and does not fabricate a
  placeholder briefing, which is the point.
- Real bug found and fixed while wiring the full pipeline: the Week 1 Data
  agent fetched and normalized events but never wrote them to the graph
  inside the LangGraph flow (that only happened via the separate
  `loader.py ingest` CLI command) -- so `build_full_graph()` would have run
  the Analyst agent against stale graph state. Fixed by having
  `data_agent_node` call the same `upsert_events()` the CLI uses, so
  `ingest` and the pipeline can't silently drift apart.
- MCP server (`src/mcp_server/server.py`): `query_competitor` and
  `get_regulatory_updates` are real, no LLM dependency, live-tested against
  Aura -- correctly distinguish "tracked with events" (Trade Republic) vs
  "tracked, no events yet" (Upvest) vs "not tracked" (nonsense input), and
  correctly pull BaFin/ESMA items with date-window filtering.
  `get_daily_briefing` is real but has nothing to serve until a Briefing
  node exists -- returns a plain "no briefing yet" message rather than an
  error, since that's a legitimate state, not a failure.
- Real bug found integrating the MCP server: the `mcp` SDK renamed
  `FastMCP` to `MCPServer` and moved it from `mcp.server.fastmcp` to
  `mcp.server.mcpserver` as of v2.0 -- the doc's original stub (written
  Week 1) used the old import and would have failed on first run. Fixed;
  same decorator-based `.tool()` API either way.
- Schema extended: `Event.briefed_at` (null until covered by a briefing) and
  a new `Briefing` node (`briefing_id`, `date`, `text_en`, `text_de`,
  `cost_usd`) linked via `COVERS`, applied live to the same Aura instance.

**Blocked on you for full Week 2 close-out:**

- `ANTHROPIC_API_KEY` -- needed to actually generate a briefing and close
  the loop (`get_daily_briefing` has something real to return, `briefed_at`
  gets set, cost-per-run becomes a real measured number instead of a
  formula). Add it to `.env`.
- `LANGCHAIN_API_KEY` (optional but the doc's observability non-negotiable
  wants it) -- tracing is coded and wired but currently disabled
  (`LANGCHAIN_TRACING_V2=false`) because a blank key just produces 401s on
  every run instead of failing quietly.
- Re-evaluate the "investment services" keyword's precision on a few more
  days of BaFin data -- unchanged from Week 1, still an Analyst-agent
  triage question rather than an ingestion one.

## Repo layout

```
config/sources.yaml       feed URLs, keyword list, tracked companies/regulators
src/ingestion/feeds.py    fetch + normalize + filter (no LLM calls)
src/graph/                Neo4j schema, seed data, Python loader (incl. Briefing storage)
src/agents/               LangGraph state + nodes (Data, Analyst, Briefing) + pipeline wiring
src/mcp_server/server.py  MCP tools: get_daily_briefing, query_competitor, get_regulatory_updates
tests/test_ingestion.py   live smoke tests against real feeds
data/                     sample ingestion output
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in NEO4J_* now; ANTHROPIC_API_KEY when ready

python -m pytest tests/ -v              # live feed smoke tests
python -m src.agents.pipeline           # fetch + upsert only (no LLM)
python -m src.agents.pipeline --full    # full Data->Analyst->Briefing (needs ANTHROPIC_API_KEY)
python -m src.agents.analyst_agent      # Analyst agent alone, no LLM needed
python -m src.graph.loader init         # apply schema to your own Neo4j instance
python -m src.graph.loader ingest       # pull feeds and upsert into that graph
python -m src.mcp_server.server         # run the MCP server (stdio)
```

## Week-by-week plan (from the scope doc)

| Week | Focus | Status |
|---|---|---|
| 1 | v1 data sources -> Neo4j schema populated; pipeline skeleton with tracing on | Done. Sources verified, ingestion live, graph populated on Aura, repo published on GitHub -- all independently verified. |
| 2 | Analyst + Briefing agents end-to-end; EN/DE toggle; MCP server wrapping the three tools | Built same day. Analyst agent + 2 of 3 MCP tools fully live-verified (no LLM needed). Briefing agent + `get_daily_briefing` implemented but blocked on `ANTHROPIC_API_KEY` to actually run. |
| 3 | Frozen-corpus eval; deploy; cost tracking; case study; publish MCP server | Not started |
