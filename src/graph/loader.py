"""
Loads normalized events (from src/ingestion/feeds.py) into this project's own
Neo4j instance -- point NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD (see .env.example)
at a dedicated instance, not the portfolio-tracking graph.

Run once to initialize:
    python -m src.graph.loader init      # applies schema.cypher + seed.cypher
    python -m src.graph.loader ingest    # pulls feeds and upserts Events
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

from src.ingestion.feeds import pull_all_events, RawEvent

try:
    from dotenv import load_dotenv

    # Explicit path: find_dotenv()'s stack-frame auto-detection breaks when
    # this runs under `python -m` or from a heredoc/REPL rather than a plain
    # script invocation -- pin it to the repo root instead of guessing.
    _ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=_ENV_PATH)
except ImportError:
    pass  # fine if python-dotenv isn't installed; env vars can be exported manually

SCHEMA_DIR = Path(__file__).parent
DATABASE = os.environ.get("NEO4J_DATABASE") or None  # Aura instances may not use "neo4j"

UPSERT_EVENT_QUERY = """
MERGE (s:Source {source_id: $source_id})
  ON CREATE SET s.name = $source_name
MERGE (e:Event {event_id: $event_id})
  SET e.title = $title, e.link = $link, e.published = $published,
      e.summary = $summary, e.category = $category
MERGE (e)-[:FROM_SOURCE]->(s)
WITH e
UNWIND $matched_companies AS company_name
  MERGE (c:Company {name: company_name})
  MERGE (e)-[:MENTIONS]->(c)
"""


def get_driver():
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USER"]
    password = os.environ["NEO4J_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, password))


def run_cypher_file(driver, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    statements = [
        s.strip()
        for s in text.split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    with driver.session(database=DATABASE) as session:
        for stmt in statements:
            # Strip full-line comments inside multi-line statements.
            cleaned = "\n".join(
                line for line in stmt.splitlines() if not line.strip().startswith("//")
            ).strip()
            if cleaned:
                session.run(cleaned)


def init_schema() -> None:
    driver = get_driver()
    try:
        run_cypher_file(driver, SCHEMA_DIR / "schema.cypher")
        run_cypher_file(driver, SCHEMA_DIR / "seed.cypher")
        print("Schema + seed applied.")
    finally:
        driver.close()


def _matched_companies(event: RawEvent, tracked_companies: list[str]) -> list[str]:
    text = f"{event.title} {event.summary}".lower()
    return [c for c in tracked_companies if c.lower() in text]


def ingest(config_path: str = "config/sources.yaml") -> None:
    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    tracked_companies = config.get("tracked_companies", [])

    events = pull_all_events(config_path)
    driver = get_driver()
    written = 0
    try:
        with driver.session(database=DATABASE) as session:
            for event in events:
                companies = _matched_companies(event, tracked_companies)
                session.run(
                    UPSERT_EVENT_QUERY,
                    source_id=event.source_id,
                    source_name=event.source_name,
                    event_id=event.event_id,
                    title=event.title,
                    link=event.link,
                    published=event.published,
                    summary=event.summary,
                    category=event.category,
                    matched_companies=companies,
                )
                written += 1
    finally:
        driver.close()
    print(f"Upserted {written} events ({len(events)} fetched).")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "init"
    if action == "init":
        init_schema()
    elif action == "ingest":
        ingest()
    else:
        print("Usage: python -m src.graph.loader [init|ingest]")
