# Case study: European Brokerage Market Intelligence Agent

**Problem.** Founder's Associate roles at fintech-infrastructure companies
like lemon.markets ask candidates to "analyse market developments,
competitor dynamics, and trends across the European brokerage, wealth, and
investment infrastructure landscape" -- and to do it in a way that scales
with AI rather than one analyst reading press releases by hand. This project
builds that responsibility as a daily agent: it pulls live news and
regulatory feeds, reasons over a graph of tracked companies and regulators,
and produces a cited, guardrail-constrained SITREP in English and German.

**Architecture and trade-offs.** A three-agent LangGraph pipeline (Data,
Analyst, Briefing) sits on top of a dedicated Neo4j Aura graph, separate
from unrelated project state by design. The Data and Analyst agents are
deliberately LLM-free: feed parsing and "which events are new" are
deterministic facts, not judgment calls, so they're cheap, fast, and
immune to hallucination before anything reaches a language model. The
Briefing agent uses Claude Haiku 4.5 rather than a larger model -- this is
bounded summarization over a small, pre-filtered input, not open-ended
reasoning, and the eval backs that choice (94-100% recall across three
post-fix trials). The non-fabrication guardrail -- "don't call something a
trend unless >=2 independent sources back it" -- is enforced in the Analyst
agent's code, not left to a prompt, precisely because a prompt is a request
and code is a guarantee.

**What I'd change at scale.** The frozen-corpus eval surfaced real
variance: the same corpus and prompt produced one run with a fabricated
URL and 50% recall, and three runs with near-perfect scores. That's not a
flaky test, it's an honest measurement of an LLM's citation reliability at
default sampling. At scale I'd add a post-generation validation step that
checks every cited URL against the corpus programmatically and rejects or
regenerates on any mismatch, rather than trusting the model to transcribe
URLs correctly every time. I'd also lower the Briefing agent's temperature,
since there's no real upside to sampling diversity in citation transcription.

**Measured outcome.** Real cost per run: $0.012-$0.022 across 8 live
trials (avg ~$0.017), using real Anthropic pricing, not an estimate. Two
real bugs found via live testing rather than assumed correct: an
`max_tokens` ceiling that silently truncated the German half of a briefing
(caught by the eval harness, not manual inspection), and a keyword-filter
bug where "BaFin"/"ESMA" matched their own source names, inflating one
day's event count from 18 to a noisier 33 before the fix. A second
cost-optimization (prompt caching) was implemented and measured honestly:
it provides zero benefit at this system prompt's current size, since
Claude Haiku 4.5 requires 4,096 cacheable tokens and this prompt is roughly
300 -- documented as inactive rather than misrepresented as a win. This
closes the gap named directly in my cover letter: institutional
brokerage/custody/BaFin/MiFID II domain knowledge, built by doing rather
than claimed.
