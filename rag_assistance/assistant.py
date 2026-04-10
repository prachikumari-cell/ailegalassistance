# rag_assistant/assistant.py
from dataclasses import dataclass
from openai import AsyncOpenAI
import faiss, numpy as np

@dataclass
class LegalOutcome:
    similar_cases:          list[dict]
    constitutional_issues:  list[str]
    petitioner_arguments:   str
    respondent_arguments:   str
    likely_outcome:         str   # "likely upheld" | "likely struck down" | "uncertain"
    confidence:             float
    judicial_reasoning:     str
    risk_factors:           list[str]

SYSTEM_PROMPT = """
You are a senior Indian constitutional law expert with 30 years of Supreme Court practice.
When analysing hypothetical cases you must:
1. Identify every constitutional provision potentially engaged
2. Map the case to the most analogous precedents
3. Apply the Doctrine of Proportionality where applicable
4. Consider the Basic Structure Doctrine for fundamental right challenges
5. Flag any tension with DPSP provisions
6. Give a reasoned prediction — never hedge without a legal basis
"""

class RAGLegalAssistant:
    def __init__(self, vector_index: faiss.Index, case_db):
        self.index    = vector_index
        self.case_db  = case_db
        self.client   = AsyncOpenAI()

    async def analyse(self, hypothetical: str) -> LegalOutcome:
        # Step 1: Retrieve similar cases via semantic search
        similar_cases = await self._retrieve_similar(hypothetical, top_k=8)

        # Step 2: Build context window
        context = self._build_rag_context(similar_cases)

        # Step 3: Generate structured legal analysis
        analysis = await self._generate_analysis(hypothetical, context)

        # Step 4: Generate adversarial arguments
        arguments = await self._generate_both_sides(hypothetical, analysis)

        return LegalOutcome(
            similar_cases         = similar_cases,
            constitutional_issues = analysis["issues"],
            petitioner_arguments  = arguments["petitioner"],
            respondent_arguments  = arguments["respondent"],
            likely_outcome        = analysis["likely_outcome"],
            confidence            = analysis["confidence"],
            judicial_reasoning    = analysis["reasoning"],
            risk_factors          = analysis["risks"],
        )

    async def _retrieve_similar(self, query: str, top_k: int) -> list[dict]:
        from .embedder import embed_text
        q_vec = await embed_text(query)
        q_arr = np.array([q_vec], dtype=np.float32)
        scores, idxs = self.index.search(q_arr, top_k)

        results = []
        for score, idx in zip(scores[0], idxs[0]):
            case = await self.case_db.get_by_vector_idx(idx)
            if case and score > 0.6:
                results.append({**case, "similarity": float(score)})
        return results

    def _build_rag_context(self, cases: list[dict]) -> str:
        lines = []
        for c in cases:
            lines.append(
                f"CASE: {c['citation']} ({c['year']})\n"
                f"RATIO: {c['ratio']}\n"
                f"VERDICT: {c['verdict']}\n"
                f"ARTICLES: {', '.join(c.get('articles_invoked', []))}\n"
            )
        return "\n---\n".join(lines)

    async def _generate_analysis(self, hypothetical: str, context: str) -> dict:
        prompt = f"""
HYPOTHETICAL CASE:
{hypothetical}

RELEVANT PRECEDENTS:
{context}

Analyse this case. Respond in JSON:
{{
  "issues": ["<constitutional question>"],
  "likely_outcome": "upheld|struck down|uncertain",
  "confidence": 0.0-1.0,
  "reasoning": "<step-by-step constitutional reasoning>",
  "risks": ["<legal risk 1>", "<legal risk 2>"]
}}
"""
        r = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
        )
        import json
        return json.loads(r.choices[0].message.content)

    async def _generate_both_sides(self, hypothetical: str, analysis: dict) -> dict:
        """Generate adversarial arguments for both petitioner and respondent."""
        prompt = f"""
Case: {hypothetical}
Constitutional issues: {analysis['issues']}

Write the best possible legal argument for:
1. PETITIONER (challenging the state action)
2. RESPONDENT (defending the state action)

Use Indian constitutional precedents. Be sharp, specific, citation-driven.
Return JSON: {{ "petitioner": "...", "respondent": "..." }}
"""
        r = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # slightly higher — we want creative legal argumentation
        )
        import json
        return json.loads(r.choices[0].message.content)