# api/main.py
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio

from conflict_engine.detector  import ConflictDetector
from rag_assistant.assistant   import RAGLegalAssistant
from prediction.future_conflicts import FutureConflictPredictor
from case_intelligence.extractor import CaseExtractor

# Startup: initialize models once (expensive)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.detector   = ConflictDetector()
    app.state.assistant  = RAGLegalAssistant(
        vector_index = await build_faiss_index(),
        case_db      = get_case_db(),
    )
    app.state.predictor  = FutureConflictPredictor(
        graph_client = get_graph(),
        case_db      = get_case_db(),
    )
    app.state.extractor  = CaseExtractor()
    yield

app = FastAPI(title="Constitutional Conflict Analyzer API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── Schemas ──────────────────────────────────────────────────
class ConflictQuery(BaseModel):
    query:    str
    top_k:    int = 5

class HypotheticalCase(BaseModel):
    facts:    str
    issue:    str
    relief:   str

class JudgmentIngest(BaseModel):
    citation: str
    text:     str

# ─── Routes ───────────────────────────────────────────────────
@app.post("/api/v1/detect-conflict")
async def detect_conflict(body: ConflictQuery):
    """Core endpoint. Returns structured conflict analysis for a legal query."""
    if len(body.query) < 10:
        raise HTTPException(400, "Query too short")
    results = await app.state.detector.detect(body.query, top_k=body.top_k)
    return {"conflicts": [r.__dict__ for r in results]}

@app.post("/api/v1/analyse-case")
async def analyse_hypothetical(body: HypotheticalCase):
    """RAG-powered legal outcome prediction for hypothetical cases."""
    scenario = f"Facts: {body.facts}\nIssue: {body.issue}\nRelief sought: {body.relief}"
    outcome  = await app.state.assistant.analyse(scenario)
    return outcome.__dict__

@app.get("/api/v1/predict-future-conflicts")
async def predict_future(top_n: int = 5):
    """Returns emerging constitutional tensions not yet litigated."""
    return await app.state.predictor.predict(top_n=top_n)

@app.get("/api/v1/heatmap")
async def get_heatmap():
    """Conflict tension heatmap data for all article pairs."""
    from graph.queries import QUERIES
    from graph.client  import GraphClient
    data = await GraphClient().run(QUERIES["heatmap_data"])
    return {"heatmap": data}

@app.get("/api/v1/timeline/{article_id}")
async def get_timeline(article_id: str):
    """How a specific article's interpretation evolved over time."""
    from graph.queries import QUERIES
    from graph.client  import GraphClient
    data = await GraphClient().run(
        QUERIES["interpretation_timeline"], art_id=article_id
    )
    return {"timeline": data}

@app.post("/api/v1/ingest-judgment")
async def ingest_judgment(body: JudgmentIngest):
    """Background-ingest a new judgment — extract, embed, persist."""
    import asyncio
    asyncio.create_task(_ingest_worker(body.citation, body.text))
    return {"status": "ingestion_queued", "citation": body.citation}

async def _ingest_worker(citation: str, text: str):
    structure = await app.state.extractor.extract(text, citation)
    await persist_to_postgres(structure)
    await persist_to_neo4j(structure)
    await persist_to_faiss(structure)

@app.websocket("/ws/debate-stream")
async def debate_stream(ws: WebSocket):
    """
    Streams adversarial debate in real-time.
    Client sends: {"query": "..."}
    Server streams: petitioner chunk → respondent chunk → verdict
    """
    await ws.accept()
    data = await ws.receive_json()
    query = data.get("query", "")

    async for chunk in stream_debate(query, app.state.assistant.client):
        await ws.send_text(chunk)

    await ws.close()
    