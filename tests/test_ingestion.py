"""
Smoke test against the LIVE feeds -- deliberately not mocked. This is the
riskiest part of the project per the scope doc, so the test that matters
most is "do the real sources still respond and parse," not a mocked unit
test that could stay green while the real feeds silently rot.
"""

from __future__ import annotations

import os

import pytest

from src.ingestion.feeds import load_sources, pull_all_events

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sources.yaml")


def test_config_loads():
    config = load_sources(CONFIG_PATH)
    assert len(config["feeds"]) >= 3
    assert "BaFin" in config["tracked_regulators"] or "ESMA" in config["tracked_regulators"]


def test_live_feeds_return_events():
    """
    Pulls all v1 feeds live. Requires network access. If this starts failing,
    it means a real source changed shape or started blocking requests --
    exactly the failure mode the doc flags as the top project risk.
    """
    events = pull_all_events(CONFIG_PATH, only_matched=False)
    assert len(events) > 0, "No items returned from any v1 feed -- check source URLs."


def test_keyword_filter_reduces_noise():
    all_events = pull_all_events(CONFIG_PATH, only_matched=False)
    matched_events = pull_all_events(CONFIG_PATH, only_matched=True)
    assert len(matched_events) <= len(all_events)
    for event in matched_events:
        assert len(event.matched_keywords) > 0


def test_event_ids_are_stable():
    """Re-running ingestion should produce the same event_id for the same item
    (needed so the graph loader upserts instead of duplicating nodes)."""
    first = {e.event_id: e for e in pull_all_events(CONFIG_PATH, only_matched=False)}
    second = {e.event_id: e for e in pull_all_events(CONFIG_PATH, only_matched=False)}
    assert set(first.keys()) == set(second.keys())
