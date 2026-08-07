# Cost optimization decisions -- measured, not assumed

The scope doc asks for "at least one optimization decision (model tiering,
caching, or batch size)" with a measured figure. This project has two, with
real numbers for both -- including one that turned out not to help, which is
itself the useful result.

## 1. Model tiering: Claude Haiku 4.5, not Sonnet or Opus

Briefing generation is bounded summarization over a small, pre-filtered,
structured input (18 events on the Week 1 corpus) -- not open-ended
reasoning. Haiku 4.5 handles this correctly (see `eval/results_2026-08-07.md`:
94-100% recall, faithful in 3/4 trials post-fix) at $1/$5 per MTok in/out,
versus $3/$15 for Sonnet 5 or $5/$25 for Opus 5 (pricing checked
docs.claude.com, 2026-08-07). Measured real cost per run: $0.012-$0.022
across 8 real trials this week, averaging ~$0.017/run.

## 2. Prompt caching: implemented, measured, doesn't help at this scale

The Briefing agent's system prompt (the citation/guardrail rules) is
identical on every call, so it's a textbook caching candidate. Implemented
via `cache_control: {"type": "ephemeral"}` on the system block
(`src/agents/briefing_agent.py`).

**Measured result: `cache_creation_input_tokens` and `cache_read_input_tokens`
are both 0 on every call, including two calls fired back-to-back with an
identical prompt.** This is not a bug -- per
docs.claude.com/en/docs/build-with-claude/prompt-caching, Claude Haiku 4.5
has a 4,096-token minimum cacheable prompt length. This system prompt is
roughly 250-300 tokens, an order of magnitude under the threshold, so the
API silently skips caching regardless of the `cache_control` hint (no error;
this is documented, expected behavior for anything under the minimum).

**What this means at scale:** caching would become the effective lever if
the system prompt grew substantially -- e.g. many few-shot examples, a
larger embedded guardrail spec, or historical context injected per run.
At its current size, it's dead code with no cost benefit, and padding the
prompt purely to clear an arbitrary token threshold would be optimizing for
a benchmark rather than a real cost, so it's left in place but documented
as currently inactive rather than removed or faked.

**Real lesson:** verify an optimization with the actual response fields
before crediting it in a case study. "I added caching" and "caching is
saving money" are different claims, and only the API's own
`cache_creation_input_tokens` / `cache_read_input_tokens` fields can tell
you which one is true.

## Bonus: two real bugs this surfaced

Building and measuring these optimizations is what caught two real
`max_tokens` truncations (2000 -> 4000 -> 8000, see git history and
`eval/results_2026-08-07.md`) -- the kind of failure a single "looks fine"
manual run would not have caught, but repeated real trials did.
