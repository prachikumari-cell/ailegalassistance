# conflict_engine/detector.py
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from openai import AsyncOpenAI

class ConflictType(str, Enum):
    STRUCTURAL   = "structural"    # right vs right (Art 19 vs Art 25)
    TEMPORAL     = "temporal"      # old law vs new interpretation
    TEXTUAL      = "textual"       # ambiguous constitutional text
    JURISDICTIONAL = "jurisdictional"  # centre vs state powers
    FUNDAMENTAL  = "fundamental"   # FR vs DPSP tension

@dataclass
class ConflictResult:
    article_a: str
    article_b: str
    conflict_type: ConflictType
    tension_score: float           # 0.0 – 1.0
    description: str
    landmark_cases: list[dict]
    resolution_principle: str
    predicted_future_risk: str

class ConflictDetector:
    CONFLICT_PAIRS = {
        ("14", "15"):  ("equality vs. protective discrimination", ConflictType.STRUCTURAL),
        ("19", "21"):  ("speech freedom vs. personal liberty", ConflictType.STRUCTURAL),
        ("19", "25"):  ("speech vs. religious sentiments",     ConflictType.STRUCTURAL),
        ("21", "22"):  ("liberty vs. preventive detention",    ConflictType.STRUCTURAL),
        ("25", "14"):  ("religious freedom vs. equal treatment", ConflictType.STRUCTURAL),
        ("32", "226"): ("SC vs HC writ jurisdiction overlap",  ConflictType.JURISDICTIONAL),
        ("39A", "246"):("legal aid vs. legislative power",     ConflictType.JURISDICTIONAL),
        ("21", "51A"): ("privacy vs. fundamental duties",      ConflictType.FUNDAMENTAL),
        ("19", "69"):  ("freedom vs. emergency restrictions",  ConflictType.TEMPORAL),
    }

    def __init__(self, model_name: str = "legal-bert-base-uncased"):
        self.embedder  = SentenceTransformer(model_name)
        self.llm       = AsyncOpenAI()
        self._build_article_index()

    def _build_article_index(self):
        """Pre-embed all constitutional articles into FAISS."""
        from .corpus import ARTICLE_CORPUS      # dict {art_id: text}
        self.article_ids   = list(ARTICLE_CORPUS.keys())
        self.article_texts = list(ARTICLE_CORPUS.values())
        embeddings = self.embedder.encode(
            self.article_texts, normalize_embeddings=True
        )
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)     # inner-product == cosine on L2-normalized
        self.index.add(embeddings.astype(np.float32))

    async def detect(self, query: str, top_k: int = 5) -> list[ConflictResult]:
        """
        Given a legal scenario, find constitutional articles in tension.
        Pipeline:
          1. Embed query → find top-k articles via FAISS
          2. Pair articles → look up known conflict map
          3. For unknown pairs → compute semantic tension score
          4. Enrich with LLM for legal reasoning
        """
        q_embed = self.embedder.encode([query], normalize_embeddings=True)
        scores, idxs = self.index.search(q_embed.astype(np.float32), top_k)

        candidate_articles = [
            (self.article_ids[i], scores[0][rank], self.article_texts[i])
            for rank, i in enumerate(idxs[0])
        ]

        conflicts: list[ConflictResult] = []
        seen_pairs: set[tuple] = set()

        for i in range(len(candidate_articles)):
            for j in range(i + 1, len(candidate_articles)):
                art_a_id, score_a, text_a = candidate_articles[i]
                art_b_id, score_b, text_b = candidate_articles[j]
                pair_key = tuple(sorted([art_a_id, art_b_id]))

                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                known = self.CONFLICT_PAIRS.get(pair_key)
                if known:
                    description, c_type = known
                    tension = 0.75  # known conflicts are high tension
                else:
                    # Semantic tension: high cosine similarity + divergent rights
                    # = likely tension
                    a_embed = self.embedder.encode([text_a], normalize_embeddings=True)
                    b_embed = self.embedder.encode([text_b], normalize_embeddings=True)
                    tension = float(np.dot(a_embed, b_embed.T)[0][0])
                    if tension < 0.3:
                        continue   # articles are too unrelated
                    description = await self._llm_describe_tension(text_a, text_b, query)
                    c_type = ConflictType.STRUCTURAL

                cases = await self._fetch_landmark_cases(pair_key)
                resolution = await self._llm_resolution_principle(text_a, text_b, cases)

                conflicts.append(ConflictResult(
                    article_a          = art_a_id,
                    article_b          = art_b_id,
                    conflict_type      = c_type,
                    tension_score      = tension,
                    description        = description,
                    landmark_cases     = cases,
                    resolution_principle = resolution,
                    predicted_future_risk = await self._predict_risk(art_a_id, art_b_id),
                ))

        conflicts.sort(key=lambda x: x.tension_score, reverse=True)
        return conflicts

    async def _llm_describe_tension(self, text_a: str, text_b: str, query: str) -> str:
        prompt = f"""
You are an expert constitutional lawyer.
Article A: {text_a}
Article B: {text_b}
Legal context: {query}

In one precise sentence, describe the constitutional tension between these two provisions.
"""
        r = await self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=120,
        )
        return r.choices[0].message.content.strip()

    async def _llm_resolution_principle(
        self, text_a: str, text_b: str, cases: list[dict]
    ) -> str:
        case_summaries = "\n".join(
            f"- {c['citation']}: {c['ratio']}" for c in cases[:3]
        )
        prompt = f"""
Constitutional provisions in conflict:
A: {text_a}
B: {text_b}

Landmark cases:
{case_summaries}

State the dominant judicial principle the Supreme Court uses to resolve this tension.
Be precise. One paragraph.
"""
        r = await self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        return r.choices[0].message.content.strip()

    async def _fetch_landmark_cases(self, pair_key: tuple) -> list[dict]:
        """Query Neo4j for cases that RESOLVES a CONFLICTS_WITH edge."""
        from .graph import GraphClient
        cypher = """
        MATCH (a:Article {id: $art_a})-[:CONFLICTS_WITH]-(b:Article {id: $art_b})
        MATCH (c:Case)-[:RESOLVES]->(conflict)
        WHERE (conflict)-[:INVOLVES]->(a) AND (conflict)-[:INVOLVES]->(b)
        RETURN c.citation AS citation,
               c.year     AS year,
               c.ratio    AS ratio,
               c.verdict  AS verdict
        ORDER BY c.year DESC
        LIMIT 5
        """
        return await GraphClient().run(cypher, art_a=pair_key[0], art_b=pair_key[1])

    async def _predict_risk(self, art_a: str, art_b: str) -> str:
        # Placeholder — replaced by full FutureConflictPredictor in Module E
        return f"Emerging risk: technology-driven reinterpretation of Art {art_a} may intensify tension with Art {art_b}."