"""
Data agent, step 1: pull + normalize RSS/regulator feeds into a common Event schema.

This is the "riskiest part of the project" per the scope doc -- heterogeneous
press pages stall projects like this. So this module does one job well:
fetch each configured feed, parse it, filter by keyword relevance, and emit
a normalized list of dicts. No LLM calls here; this is deterministic ingestion,
kept separate from the reasoning agents so it can be tested and cached cheaply.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
import yaml

USER_AGENT = "Mozilla/5.0 (compatible; EuroBrokerageIntelAgent/0.1; +https://github.com/)"
REQUEST_TIMEOUT = 15.0


@dataclass
class RawEvent:
    """A single normalized item pulled from a feed, pre-graph-write."""

    event_id: str
    source_id: str
    source_name: str
    category: str
    title: str
    link: str
    published: str | None
    summary: str
    matched_keywords: list[str] = field(default_factory=list)
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_sources(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_event_id(source_id: str, link: str) -> str:
    """Stable id so re-runs upsert instead of duplicating graph nodes."""
    digest = hashlib.sha256(f"{source_id}:{link}".encode("utf-8")).hexdigest()
    return digest[:16]


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def fetch_feed(source: dict[str, Any], client: httpx.Client) -> feedparser.FeedParserDict:
    resp = client.get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def pull_all_events(
    config_path: str = "config/sources.yaml",
    only_matched: bool = True,
) -> list[RawEvent]:
    """
    Fetch every configured feed, normalize entries, and filter to items that
    match at least one tracked keyword (unless only_matched=False, useful for
    debugging a feed that's returning zero matches).
    """
    config = load_sources(config_path)
    keywords = config.get("keywords", [])
    events: list[RawEvent] = []
    errors: list[dict[str, str]] = []

    with httpx.Client(follow_redirects=True) as client:
        for source in config["feeds"]:
            try:
                parsed = fetch_feed(source, client)
            except Exception as exc:  # noqa: BLE001 - want to keep going on partial failure
                errors.append({"source_id": source["id"], "error": str(exc)})
                continue

            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated"))

                matched = _match_keywords(f"{title} {summary}", keywords)
                if only_matched and not matched:
                    continue

                events.append(
                    RawEvent(
                        event_id=_make_event_id(source["id"], link or title),
                        source_id=source["id"],
                        source_name=source["name"],
                        category=source.get("category", "unknown"),
                        title=title,
                        link=link,
                        published=published,
                        summary=summary[:1000],
                        matched_keywords=matched,
                    )
                )

    if errors:
        # Surface fetch failures loudly rather than silently under-reporting --
        # matches the project's non-fabrication / cite-everything discipline:
        # an agent that goes quiet about a broken source is its own kind of
        # fabrication by omission.
        for err in errors:
            print(f"[fetch_feed] WARNING: {err['source_id']} failed: {err['error']}")

    return events


if __name__ == "__main__":
    import json
    import sys

    config_arg = sys.argv[1] if len(sys.argv) > 1 else "config/sources.yaml"
    results = pull_all_events(config_arg, only_matched=False)
    print(f"Fetched {len(results)} total items across all feeds (pre-keyword-filter shown).")
    matched = [e for e in results if e.matched_keywords]
    print(f"{len(matched)} matched at least one tracked keyword.")
    print(json.dumps([e.to_dict() for e in matched], indent=2)[:2000])
