# case_intelligence/extractor.py
from pydantic import BaseModel
from openai import AsyncOpenAI
import asyncio

class CaseStructure(BaseModel):
    citation:    str
    court:       str
    year:        int
    bench_size:  int

    # IRAC decomposition
    facts:       str   # compressed narrative
    issues:      list[str]  # each is one constitutional question
    arguments:   dict[str, str]  # {"petitioner": ..., "respondent": ...}
    ratio:       str   # the binding legal principle
    obiter:      str   # non-binding observations
    verdict:     str   # "upheld" | "struck down" | "remanded"

    # Conflict metadata
    articles_invoked: list[str]
    articles_violated: list[str]
    overrules:   list[str]   # citations of overruled cases
    follows:     list[str]   # citations of followed cases

    # Embeddings (populated separately)
    ratio_embedding:  list[float] | None = None
    facts_embedding:  list[float] | None = None

class CaseExtractor:
    EXTRACTION_PROMPT = """
You are an expert Indian constitutional law researcher.

Extract structured information from the following Supreme Court judgment.

OUTPUT STRICT JSON matching this schema:
{
  "facts": "<2-3 sentence factual background>",
  "issues": ["<constitutional question 1>", "<constitutional question 2>"],
  "arguments": {
    "petitioner": "<key argument>",
    "respondent": "<key argument>"
  },
  "ratio": "<the binding ratio decidendi — the rule of law established>",
  "obiter": "<significant obiter dicta if any, else null>",
  "verdict": "<upheld|struck down|remanded|dismissed>",
  "articles_invoked": ["14", "21", "19"],
  "articles_violated": ["21"],
  "overrules": ["AIR 1950 SC 27"],
  "follows": ["(1978) 1 SCC 248"]
}

JUDGMENT TEXT:
{text}
"""

    def __init__(self):
        self.client = AsyncOpenAI()

    async def extract(self, judgment_text: str, citation: str) -> CaseStructure:
        # Chunk if > 12k tokens (approx 48k chars)
        if len(judgment_text) > 48_000:
            structure = await self._extract_chunked(judgment_text)
        else:
            structure = await self._extract_single(judgment_text)

        # Populate embeddings
        from .embedder import EmbeddingService
        emb = EmbeddingService()
        structure.ratio_embedding = await emb.embed(structure.ratio)
        structure.facts_embedding = await emb.embed(structure.facts)

        return structure

    async def _extract_single(self, text: str) -> CaseStructure:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": self.EXTRACTION_PROMPT.format(text=text[:48_000])
            }],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        import json
        data = json.loads(response.choices[0].message.content)
        return CaseStructure(**data)

    async def _extract_chunked(self, text: str) -> CaseStructure:
        """
        Map-reduce extraction:
        1. Split judgment into chunks
        2. Extract partial structure from each
        3. Merge + reconcile with final LLM call
        """
        chunk_size = 40_000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        partial_results = await asyncio.gather(
            *[self._extract_single(chunk) for chunk in chunks]
        )

        # Merge: ratio from last chunk (usually conclusion), facts from first
        merged = partial_results[0].model_copy()
        if len(partial_results) > 1:
            last = partial_results[-1]
            merged.ratio    = last.ratio or merged.ratio
            merged.verdict  = last.verdict or merged.verdict
            all_issues = []
            for r in partial_results:
                all_issues.extend(r.issues)
            merged.issues = list(dict.fromkeys(all_issues))  # dedupe, preserve order

        return merged