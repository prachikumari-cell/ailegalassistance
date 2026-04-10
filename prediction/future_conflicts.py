# prediction/future_conflicts.py
"""
Identifies emerging constitutional tensions before they reach the courts.
Method: co-citation graph analysis + semantic drift detection + news signal.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
from collections import defaultdict

class FutureConflictPredictor:

    EMERGING_DOMAINS = [
        ("AI surveillance", ["21", "19(1)(d)", "19(1)(a)"],
         "State-deployed AI surveillance systems and biometric tracking vs right to privacy under Art 21 (Puttaswamy) and freedom of movement"),
        ("Sedition vs free speech", ["124A", "19(1)(a)", "19(2)"],
         "IPC 124A sedition after Supreme Court suspension — legislative vs judicial tension"),
        ("UAPA and Art 21", ["UAPA", "21", "22"],
         "Prolonged pre-trial detention under UAPA and the bail-as-rule norm under Art 21"),
        ("Reservation ceiling", ["15(4)", "16(4)", "14", "335"],
         "50% cap on reservations (Indra Sawhney) vs emerging sub-classification within SC/ST"),
        ("LGBTQ+ and Art 25", ["21", "25", "14", "15"],
         "Gender identity recognition under Art 21 dignity vs religious personal law exemptions"),
        ("Climate rights", ["21", "48A", "51A(g)"],
         "Constitutionalizing right to clean environment — expansion of Art 21 scope"),
        ("Platform speech", ["19(1)(a)", "19(2)", "21"],
         "IT Rules 2021 content takedown mechanisms and intermediary liability"),
    ]

    def __init__(self, graph_client, case_db):
        self.graph  = graph_client
        self.cases  = case_db

    async def predict(self, top_n: int = 5) -> list[dict]:
        """
        Three-signal ensemble:
        Signal 1: Co-citation graph anomalies (articles appearing together without conflict nodes)
        Signal 2: Semantic drift (year-on-year embedding shift in article interpretation)
        Signal 3: Domain-seeded heuristics (hardcoded emerging issues above)
        """
        s1 = await self._co_citation_signal()
        s2 = await self._semantic_drift_signal()
        s3 = self._domain_heuristic_signal()

        # Merge signals with weights
        all_signals = defaultdict(float)
        for pair, score in s1.items():
            all_signals[pair] += 0.4 * score
        for pair, score in s2.items():
            all_signals[pair] += 0.35 * score
        for domain, score in s3.items():
            all_signals[domain] += 0.25 * score

        ranked = sorted(all_signals.items(), key=lambda x: x[1], reverse=True)
        return [{"conflict": k, "risk_score": round(v, 3)} for k, v in ranked[:top_n]]

    async def _co_citation_signal(self) -> dict:
        """Articles co-cited 3+ times in recent cases without a CONFLICTS_WITH edge."""
        rows = await self.graph.run("""
            MATCH (c:Case)-[:INTERPRETS]->(a:Article)
            MATCH (c)-[:INTERPRETS]->(b:Article)
            WHERE id(a) < id(b) AND c.year >= 2018
            AND NOT (a)-[:CONFLICTS_WITH]-(b)
            WITH a.id + ' vs ' + b.id AS pair, count(c) AS n
            WHERE n >= 3
            RETURN pair, toFloat(n) / 10.0 AS score
        """)
        return {r["pair"]: r["score"] for r in rows}

    async def _semantic_drift_signal(self) -> dict:
        """
        Detect articles whose judicial interpretation is drifting semantically.
        High drift in two related articles = emerging tension.
        """
        # Get embeddings of all ratio decidendi from 2010-2017 vs 2018-2024
        # Compute centroid shift per article
        # High centroid shift + overlapping articles = emerging conflict

        drifts = {}
        article_ids = ["14", "19", "21", "25", "32"]

        for art_id in article_ids:
            old_cases = await self.cases.get_by_article_year(art_id, 2010, 2017)
            new_cases = await self.cases.get_by_article_year(art_id, 2018, 2024)

            if not old_cases or not new_cases:
                continue

            old_embeds = np.array([c["ratio_embedding"] for c in old_cases])
            new_embeds = np.array([c["ratio_embedding"] for c in new_cases])

            old_centroid = normalize(old_embeds).mean(axis=0)
            new_centroid = normalize(new_embeds).mean(axis=0)

            drift = float(1 - np.dot(old_centroid, new_centroid))
            drifts[f"Art {art_id} drift"] = drift

        return drifts

    def _domain_heuristic_signal(self) -> dict:
        """Return domain-seeded emerging conflict signals with static risk scores."""
        return {
            domain: 0.8  # all seeded domains are high-priority
            for domain, articles, description in self.EMERGING_DOMAINS
        }