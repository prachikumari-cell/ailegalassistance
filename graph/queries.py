QUERIES = {

    # Find all cases that resolved tension between two articles
    "cases_resolving_conflict": """
        MATCH (a:Article {id: $art_a})-[:CONFLICTS_WITH]-(b:Article {id: $art_b})
        MATCH (cf:Conflict)-[:INVOLVES]->(a)
        MATCH (cf)-[:INVOLVES]->(b)
        MATCH (c:Case)-[:RESOLVES]->(cf)
        OPTIONAL MATCH (j:Judge)-[:AUTHORED]->(c)
        RETURN c.citation, c.year, c.verdict, c.ratio,
               collect(j.name) AS judges
        ORDER BY c.year DESC
    """,

    # Find the shortest reasoning path from Article X to Principle Y
    "reasoning_chain": """
        MATCH path = shortestPath(
          (a:Article {id: $art_id})-[*..6]-(p:Principle {name: $principle})
        )
        RETURN [node in nodes(path) | labels(node)[0] + ': ' +
               coalesce(node.id, node.name, node.citation)] AS chain,
               length(path) AS depth
    """,

    # Judge ideology analysis — which judges expanded vs. restricted a right
    "judge_ideology": """
        MATCH (j:Judge)-[:AUTHORED]->(c:Case)-[:INTERPRETS]->(a:Article {id: $art_id})
        WITH j, c, a
        MATCH (c)-[:RESOLVES]->(cf:Conflict)-[:INVOLVES]->(a)
        RETURN j.name, cf.type,
               c.verdict,
               count(*) AS decision_count
        ORDER BY decision_count DESC
    """,

    # Conflict heatmap data — tension scores between all article pairs
    "heatmap_data": """
        MATCH (a:Article)-[r:CONFLICTS_WITH]-(b:Article)
        WHERE id(a) < id(b)
        RETURN a.id AS art_a, b.id AS art_b,
               r.tension_score AS score,
               r.conflict_type AS type,
               count{ (c:Case)-[:RESOLVES]->(:Conflict)-[:INVOLVES]->(a),
                      (c)-[:RESOLVES]->(:Conflict)-[:INVOLVES]->(b) } AS case_count
        ORDER BY score DESC
    """,

    # Timeline: how interpretation of an article evolved over decades
    "interpretation_timeline": """
        MATCH (c:Case)-[:INTERPRETS]->(a:Article {id: $art_id})
        OPTIONAL MATCH (p:Principle)<-[:ESTABLISHES]-(c)
        RETURN c.year, c.citation, c.verdict,
               collect(p.name) AS principles_established
        ORDER BY c.year ASC
    """,

    # Emerging risk: articles often co-cited recently without a Conflict node
    "emerging_conflicts": """
        MATCH (c:Case)-[:INTERPRETS]->(a:Article)
        MATCH (c)-[:INTERPRETS]->(b:Article)
        WHERE id(a) < id(b) AND c.year >= 2015
        AND NOT (a)-[:CONFLICTS_WITH]-(b)
        WITH a, b, count(c) AS co_citations
        WHERE co_citations >= 3
        RETURN a.id, b.id, co_citations
        ORDER BY co_citations DESC
        LIMIT 20
    """,
}