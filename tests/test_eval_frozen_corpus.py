"""
Frozen-corpus eval -- Week 3, per the scope doc's evaluation method:

    "freeze a news corpus from one past week with known ground-truth events
    ... run the pipeline blind against the frozen corpus and score: did the
    briefing surface each ground-truth event (recall), did it fabricate or
    over-claim anything not in the corpus (faithfulness), and were all
    claims cited?"

Corpus: data/sample_run_2026-08-07.json -- the real, live-fetched 18 events
from the Week 1 pull. Ground truth is defined independently by inspecting
the corpus data itself (below), not by looking at any briefing text, so
scoring the briefing against it is a real check, not a circular one.

Makes a real, paid Anthropic API call (this is the actual generation being
evaluated, not mocked) -- run deliberately, not on every CI push.

Run directly: python -m tests.test_eval_frozen_corpus
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from src.agents.analyst_agent import _flag_trends
from src.agents.briefing_agent import generate_sitrep
from src.graph.loader import _matched_companies

CORPUS_PATH = Path(__file__).parent.parent / "data" / "sample_run_2026-08-07.json"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"

# Ground truth, defined by reading the frozen corpus directly (see
# data/sample_run_2026-08-07.json) -- every item is a genuinely distinct
# reportable event as of 2026-08-07. This is deliberately "all 18," not a
# hand-picked easy subset: the corpus is small enough that a briefing which
# silently drops an item is a real recall miss worth catching, not noise.
EXPECTED_EVENT_COUNT = 18

URL_RE = re.compile(r"https?://[^\s)\]]+")

# Negation cues checked near the word "trend"/"Trend" (same spelling in
# German). The guardrail requires the model to SAY there are no trends when
# none of the events qualify -- so the word appearing isn't a violation by
# itself. What would be a violation: a sentence containing "trend" with none
# of these nearby, i.e. an unhedged positive trend claim.
TREND_NEGATION_CUES = [
    "no trend", "not a trend", "single-sourced", "no cross-source",
    "kein trend", "keine trend", "einzelquelle", "keine quellübergreifenden",
]


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:)")


def _check_trend_guardrail(text: str) -> dict:
    """Split into sentences, flag any sentence mentioning 'trend' without a
    nearby negation cue as a possible unhedged trend claim, for manual
    review -- a real NLI-based check is future work, this just narrows what
    a human needs to look at instead of reading the whole briefing."""
    sentences = re.split(r"(?<=[.!\n])\s+", text)
    trend_sentences = [s for s in sentences if "trend" in s.lower()]
    unhedged = [
        s for s in trend_sentences
        if not any(cue in s.lower() for cue in TREND_NEGATION_CUES)
    ]
    return {
        "trend_sentences_found": len(trend_sentences),
        "unhedged_trend_sentences": unhedged,
        "guardrail_appears_honored": len(unhedged) == 0,
    }


def _load_frozen_corpus() -> list[dict]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        raw_events = json.load(f)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    tracked_companies = config.get("tracked_companies", [])

    # Reshape into the same dict shape analyst_agent_node hands to the
    # Briefing agent, without touching the live graph.
    class _Event:
        def __init__(self, d):
            self.title = d["title"]
            self.summary = d["summary"]

    events = []
    for d in raw_events:
        companies = _matched_companies(_Event(d), tracked_companies)
        events.append(
            {
                "event_id": d["event_id"],
                "title": d["title"],
                "link": d["link"],
                "published": d["published"],
                "summary": d["summary"],
                "category": d["category"],
                "companies": companies,
                "source_id": d["source_id"],
                "source_name": d["source_name"],
            }
        )
    return events


def run_eval() -> dict:
    assert CORPUS_PATH.exists(), f"Frozen corpus not found at {CORPUS_PATH}"
    events = _load_frozen_corpus()
    assert len(events) == EXPECTED_EVENT_COUNT, (
        f"Corpus drifted: expected {EXPECTED_EVENT_COUNT} events, found {len(events)}. "
        "This eval is only meaningful against the frozen 2026-08-07 corpus."
    )

    annotated, trending_companies = _flag_trends(events)
    analysis_notes = (
        f"{len(annotated)} un-briefed event(s) since the last run.\n"
        + (
            f"Trend flagged (>=2 independent sources): {', '.join(sorted(trending_companies))}."
            if trending_companies
            else "No cross-source trends this run -- every event is single-sourced. "
            "Per the non-fabrication guardrail, none of today's items may be "
            "described as a 'trend' in the briefing."
        )
    )

    result = generate_sitrep(annotated, analysis_notes)

    known_links = {_clean_url(e["link"]) for e in events}

    scores = {}
    for lang in ("en", "de"):
        text = result[f"briefing_{lang}"]
        cited_links = {_clean_url(u) for u in URL_RE.findall(text)}

        recalled = known_links & cited_links
        fabricated = cited_links - known_links

        scores[lang] = {
            "recall": len(recalled) / len(known_links),
            "recalled_count": len(recalled),
            "total_count": len(known_links),
            "fabricated_urls": sorted(fabricated),
            "faithful": len(fabricated) == 0,
            "missing_events": sorted(
                e["title"] for e in events if _clean_url(e["link"]) not in cited_links
            ),
            **_check_trend_guardrail(text),
        }

    return {
        "corpus_size": len(events),
        "cost_usd": result["cost_usd"],
        "stop_reason": result["stop_reason"],
        "truncated": result["stop_reason"] == "max_tokens",
        "scores": scores,
    }


def run_eval_trials(n: int = 3) -> list[dict]:
    """
    A single trial isn't enough to characterize an LLM-backed pipeline --
    found this out by accident: a first scored run showed 50% recall and one
    fabricated URL, and an ad-hoc second call for debugging scored perfectly
    on the same corpus. That's real run-to-run variance (default sampling,
    not temperature=0), not a flaky eval. Running N trials and reporting the
    spread is the honest version of this eval; a single N=1 number would
    have overstated confidence either direction.
    """
    return [run_eval() for _ in range(n)]


if __name__ == "__main__":
    import sys

    n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    trials = run_eval_trials(n_trials)

    print(json.dumps(trials, indent=2))

    print(f"\n--- Summary across {n_trials} trial(s) ---")
    total_cost = sum(t["cost_usd"] for t in trials)
    print(f"Total cost: ${total_cost:.6f} (avg ${total_cost / n_trials:.6f}/run)")
    truncated_count = sum(1 for t in trials if t["truncated"])
    print(f"Truncated (max_tokens hit): {truncated_count}/{n_trials}")

    for lang in ("en", "de"):
        recalls = [t["scores"][lang]["recall"] for t in trials]
        faithful_count = sum(1 for t in trials if t["scores"][lang]["faithful"])
        guardrail_count = sum(1 for t in trials if t["scores"][lang]["guardrail_appears_honored"])
        print(
            f"{lang.upper()}: recall {min(recalls):.0%}-{max(recalls):.0%} "
            f"(avg {sum(recalls)/len(recalls):.0%}) across {n_trials} trials | "
            f"faithful in {faithful_count}/{n_trials} | "
            f"trend guardrail honored in {guardrail_count}/{n_trials}"
        )
        for i, t in enumerate(trials):
            s = t["scores"][lang]
            if s["fabricated_urls"]:
                print(f"  trial {i}: FABRICATED {s['fabricated_urls']}")
