# graph/schema.py  — run once to initialize the graph
NEO4J_SCHEMA_CYPHER = """
// ─── Node constraints ───────────────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article)   REQUIRE a.id       IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case)      REQUIRE c.citation IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Principle) REQUIRE p.name     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (j:Judge)     REQUIRE j.name     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cf:Conflict) REQUIRE cf.id      IS UNIQUE;

// ─── Vector index on Case.embedding (Neo4j 5.x) ─────────────────────────
CREATE VECTOR INDEX case_embedding_index IF NOT EXISTS
  FOR (c:Case) ON (c.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } };

// ─── Full-text index for judgment text search ────────────────────────────
CREATE FULLTEXT INDEX case_fulltext IF NOT EXISTS
  FOR (c:Case) ON EACH [c.facts, c.ratio, c.obiter];
"""

