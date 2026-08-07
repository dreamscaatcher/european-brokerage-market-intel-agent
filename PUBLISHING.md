# Publishing checklist -- drafted 2026-08-07, not yet submitted

Everything below is ready to copy-paste. All of it needs your own logins
(GitHub OAuth for the official registry, your accounts for the community
directories, your LinkedIn for the post) -- nothing here can be submitted
from the sandbox, same reasoning as the git pushes this week.

## Option A -- lowest friction: community directories (recommended first)

These just want a repo link and description, no package publishing
required. Do these first; they're most of the "listed on a directory"
deliverable for near-zero extra work.

**glama.ai/mcp** -- form-based, manually reviewed:
<https://glama.ai/mcp/servers/chatmcp/mcp-server-collector/tools/submit-mcp-server>
Fields to paste in:
- Name: `european-brokerage-market-intel`
- Description: "Daily market intelligence agent over the European
  brokerage/custody/wealth-infrastructure space -- competitor moves,
  funding rounds, BaFin/ESMA regulatory updates. 3 tools: get_daily_briefing
  (EN/DE), query_competitor, get_regulatory_updates."
- Repository: `https://github.com/dreamscaatcher/european-brokerage-market-intel-agent`
- Transport: stdio
- Tool count: 3
- Install: `python -m src.mcp_server.server` (see README for Claude Desktop config)

**mcp.so** -- browse their submission page (URL changes; search "mcp.so
submit server" from their homepage) and use the same fields as above.

**punkpeye/awesome-mcp-servers** -- open a PR against
<https://github.com/punkpeye/awesome-mcp-servers> adding one line under the
relevant category (Finance/Business or similar):
```
- [european-brokerage-market-intel-agent](https://github.com/dreamscaatcher/european-brokerage-market-intel-agent) - Daily European brokerage/fintech market intelligence SITREP with BaFin/ESMA regulatory tracking, EN/DE output.
```

## Option B -- official registry (registry.modelcontextprotocol.io)

Bigger lift: the official registry requires the server to be published as
an actual package (PyPI, npm, Docker Hub) with a matching `mcp-name` marker,
or an MCPB release artifact -- source code in a GitHub repo alone isn't
enough. Worth doing eventually for maximum discoverability, but Option A
gets the doc's "published + listed" deliverable done today without a
packaging detour. If/when you want to do this:

1. Package `src/mcp_server` for PyPI (needs a `pyproject.toml`, not present
   yet -- this repo currently isn't set up as an installable package).
2. Add `mcp-name: io.github.dreamscaatcher/european-brokerage-market-intel-agent`
   to the README (becomes the PyPI description).
3. `pip install mcp-publisher` (or the Homebrew/binary install), then:
   ```
   mcp-publisher login github
   mcp-publisher init      # generates server.json
   mcp-publisher publish
   ```

Draft `server.json` for when you get there:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.github.dreamscaatcher/european-brokerage-market-intel-agent",
  "description": "Daily market intelligence agent over the European brokerage/custody/wealth-infrastructure space: competitor moves, funding rounds, BaFin/ESMA regulatory updates, EN/DE SITREP.",
  "version": "1.0.0",
  "packages": [
    {
      "registry_type": "pypi",
      "identifier": "european-brokerage-market-intel-agent",
      "version": "1.0.0"
    }
  ]
}
```

## LinkedIn post (draft)

> Shipped a small side project this week: a daily market-intelligence
> agent for the European brokerage / custody / wealth-infrastructure
> space -- Trade Republic, Scalable Capital, Upvest, and the BaFin/ESMA
> regulatory feeds that govern them.
>
> It's a 3-agent LangGraph pipeline (Data -> Analyst -> Briefing) over a
> Neo4j graph, publishes a cited SITREP in English and German, and ships
> as an MCP server so it plugs straight into Claude Desktop.
>
> A few things I made sure to actually measure rather than just claim:
> - Real cost per run: $0.012-$0.022 (Claude Haiku 4.5 -- picked
>   deliberately, not by default)
> - A frozen-corpus eval that caught real citation-fabrication risk at
>   default sampling (94-100% recall across most trials, one real
>   fabricated URL in another -- both true, and now both documented)
> - A non-fabrication guardrail enforced in code, not just prompted: it
>   won't call something a "trend" unless 2+ independent sources back it
>
> Repo, case study, and eval results:
> https://github.com/dreamscaatcher/european-brokerage-market-intel-agent
>
> #AIAgents #LangGraph #MCP #Fintech #BuildInPublic

(Adjust tone/length to taste -- this is a first draft, not a final version.)
