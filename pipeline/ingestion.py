# pipeline/ingestion.py
"""
Production data pipeline using asyncio + rate-limiting.
Ingests ~50,000 Supreme Court judgments from Indian Kanoon.
"""
import asyncio, aiohttp, re
from pathlib import Path
from typing import AsyncGenerator

class IndianKanoonScraper:
    BASE_URL   = "https://api.indiankanoon.org"
    RATE_LIMIT = 2          # requests/second
    SEMAPHORE  = asyncio.Semaphore(10)

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Token {self.api_key}"}
        )
        return self

    async def __aexit__(self, *_):
        await self.session.close()

    async def search_constitutional_cases(
        self, article_id: str, page: int = 0
    ) -> dict:
        """Search for all cases mentioning a specific constitutional article."""
        async with self.SEMAPHORE:
            await asyncio.sleep(1 / self.RATE_LIMIT)
            url = f"{self.BASE_URL}/search/?formInput=Article+{article_id}+Constitution+India&pagenum={page}"
            async with self.session.get(url) as resp:
                return await resp.json()

    async def get_judgment(self, doc_id: str) -> str:
        async with self.SEMAPHORE:
            await asyncio.sleep(1 / self.RATE_LIMIT)
            url = f"{self.BASE_URL}/doc/{doc_id}/"
            async with self.session.get(url) as resp:
                data = await resp.json()
                return self._clean_judgment(data.get("doc", ""))

    def _clean_judgment(self, raw: str) -> str:
        # Strip HTML, normalize whitespace, remove boilerplate headers
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+",     " ", text)
        text = re.sub(r"REPORTABLE|NOT REPORTABLE|IN THE SUPREME COURT OF INDIA", "", text)
        return text.strip()

    async def stream_all_constitutional_cases(
        self, article_ids: list[str]
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Yield (doc_id, judgment_text) for all constitutional cases."""
        for art_id in article_ids:
            page = 0
            while True:
                results = await self.search_constitutional_cases(art_id, page)
                docs = results.get("docs", [])
                if not docs:
                    break
                for doc in docs:
                    text = await self.get_judgment(doc["tid"])
                    if len(text) > 500:   # filter stubs
                        yield doc["tid"], text
                page += 1

# Pipeline runner
async def run_full_ingestion():
    from case_intelligence.extractor import CaseExtractor
    extractor = CaseExtractor()

    CONSTITUTIONAL_ARTICLES = [
        "12", "13", "14", "15", "16", "17", "19", "20", "21",
        "21A", "22", "23", "24", "25", "26", "32", "226", "368"
    ]

    async with IndianKanoonScraper(api_key="YOUR_KEY") as scraper:
        async for doc_id, text in scraper.stream_all_constitutional_cases(CONSTITUTIONAL_ARTICLES):
            try:
                structure = await extractor.extract(text, citation=doc_id)
                await asyncio.gather(
                    persist_to_postgres(structure),
                    persist_to_neo4j(structure),
                    upsert_faiss_embedding(structure),
                )
                print(f"Ingested: {doc_id}")
            except Exception as e:
                print(f"Failed {doc_id}: {e}")
                continue