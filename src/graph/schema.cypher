// Neo4j schema for the European Brokerage Market Intelligence Agent.
//
// IMPORTANT: run this against a NEW Neo4j instance dedicated to this project
// (e.g. a free Neo4j Aura instance, or a local `docker run neo4j`) -- NOT the
// portfolio-tracking graph used for the FlagshipProject/CheckIn/Artifact nodes.
// Keeping the domain graph and the meta-tracking graph separate avoids the two
// ever colliding on labels or getting mixed up in a query.
//
// Node types
// ----------
// Company        -- a tracked brokerage/custody/wealth-infra company
// Regulator      -- BaFin, ESMA, etc.
// Event          -- a single news item (funding round, partnership, regulatory
//                   update, etc.) normalized from a feed. e.briefed_at (added
//                   Week 2) is null until an Event has been included in a
//                   Briefing -- this is how the Analyst agent finds "new or
//                   changed" items instead of re-surfacing the same events
//                   on every run.
// Source         -- the feed an Event came from, for provenance/citation
// Briefing       -- (added Week 2) one generated SITREP: briefing_id, date,
//                   text_en, text_de, cost_usd
//
// Relationship types
// -------------------
// (:Event)-[:MENTIONS]->(:Company)
// (:Event)-[:ISSUED_BY]->(:Regulator)          -- for regulatory-update events
// (:Event)-[:FROM_SOURCE]->(:Source)           -- provenance, required for the
//                                                  "cite every claim" guardrail
// (:Company)-[:PARTNERS_WITH {since, eventId}]->(:Company)
// (:Regulator)-[:REGULATES]->(:Company)
// (:Briefing)-[:COVERS]->(:Event)              -- which events a SITREP drew on

// --- Constraints (uniqueness + existence) ---

CREATE CONSTRAINT company_name_unique IF NOT EXISTS
FOR (c:Company) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT regulator_name_unique IF NOT EXISTS
FOR (r:Regulator) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT source_id_unique IF NOT EXISTS
FOR (s:Source) REQUIRE s.source_id IS UNIQUE;

CREATE CONSTRAINT briefing_id_unique IF NOT EXISTS
FOR (b:Briefing) REQUIRE b.briefing_id IS UNIQUE;

// --- Indexes for common lookups ---

CREATE INDEX event_published_idx IF NOT EXISTS
FOR (e:Event) ON (e.published);

CREATE INDEX event_category_idx IF NOT EXISTS
FOR (e:Event) ON (e.category);

CREATE INDEX event_briefed_at_idx IF NOT EXISTS
FOR (e:Event) ON (e.briefed_at);

CREATE INDEX briefing_date_idx IF NOT EXISTS
FOR (b:Briefing) ON (b.date);

// --- Upsert pattern used by the Data agent for every ingested item ---
// (params: $event_id, $title, $link, $published, $summary, $category,
//          $source_id, $source_name, $matched_companies: list[str])
//
// MERGE (s:Source {source_id: $source_id})
//   ON CREATE SET s.name = $source_name
// MERGE (e:Event {event_id: $event_id})
//   SET e.title = $title, e.link = $link, e.published = $published,
//       e.summary = $summary, e.category = $category
// MERGE (e)-[:FROM_SOURCE]->(s)
// WITH e
// UNWIND $matched_companies AS company_name
//   MERGE (c:Company {name: company_name})
//   MERGE (e)-[:MENTIONS]->(c)
