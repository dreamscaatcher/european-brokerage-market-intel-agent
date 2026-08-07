// Seed data: tracked companies and regulators.
// Run once after schema.cypher, against the project's own Neo4j instance.

MERGE (:Company {name: "Trade Republic"});
MERGE (:Company {name: "Scalable Capital"});
MERGE (:Company {name: "Upvest"});
MERGE (:Company {name: "dwpbank"});
MERGE (:Company {name: "lemon.markets"});

MERGE (:Regulator {name: "BaFin"});
MERGE (:Regulator {name: "ESMA"});
