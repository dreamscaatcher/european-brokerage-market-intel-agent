# European Brokerage Market Intelligence Agent

Daily "market SITREP" agent over the European brokerage / custody / investment-
infrastructure space: competitor moves, funding rounds, partnerships, and
regulatory developments (BaFin/ESMA). Built for the lemon.markets Founder's
Associate application; stands on its own as a portfolio flagship regardless
of that outcome.

Full scope, rationale, eval method, and timeline: see the project scope doc.
This README tracks build status against that plan.

## Status: Week 1 nearly closed out (kicked off 2026-08-07)

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

**Left for Week 1 close-out:**

- Push this repo to GitHub (`git@github.com:dreamscaatcher/european-brokerage-market-intel-agent.git`)
  from your own machine -- sandbox git pushes are avoided per the FUSE
  lock-file lesson from the Ops Intel Agent project.
- Re-evaluate the "investment services" keyword's precision on a few more
  days of BaFin data -- today's 7 matches are mostly consumer-warning items
  about unauthorized providers, which is real regulatory-enforcement signal
  but not quite "competitor moves" either. Likely an Analyst-agent triage
  problem (Week 2), not an ingestion problem.

## Repo layout

```
config/sources.yaml       feed URLs, keyword list, tracked companies/regulators
src/ingestion/feeds.py    fetch + normalize + filter (no LLM calls)
src/graph/                Neo4j schema, seed data, Python loader
src/agents/               LangGraph state + nodes + pipeline wiring
src/mcp_server/server.py  MCP tool stubs (get_daily_briefing, query_competitor,
                           get_regulatory_updates) -- Week 2
tests/test_ingestion.py   live smoke tests against real feeds
data/                     sample ingestion output
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in NEO4J_* and ANTHROPIC_API_KEY when ready

python -m pytest tests/ -v          # live feed smoke tests
python -m src.agents.pipeline       # Week 1 pipeline (Data agent only)
python -m src.graph.loader init     # apply schema to your own Neo4j instance
python -m src.graph.loader ingest   # pull feeds and upsert into that graph
```

## Week-by-week plan (from the scope doc)

| Week | Focus | Status |
|---|---|---|
| 1 | v1 data sources -> Neo4j schema populated; pipeline skeleton with tracing on | Sources verified, ingestion live, graph populated and independently verified on Aura. Only the GitHub push is outstanding. |
| 2 | Analyst + Briefing agents end-to-end; EN/DE toggle; MCP server wrapping the three tools | Not started |
| 3 | Frozen-corpus eval; deploy; cost tracking; case study; publish MCP server | Not started |
