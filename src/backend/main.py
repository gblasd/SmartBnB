"""
PropSearch FastAPI backend.

Endpoints:
  GET  /health              — liveness probe
  GET  /properties          — list all seeded properties (no AI)
  POST /search              — pure vector similarity search (no LLM)
  POST /chat                — agent chat with memory (LLM + vector DB)
  POST /chat/reset          — clear agent memory for a session
  GET  /db/status           — Chroma collection stats
"""

import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.properties import PROPERTIES
from backend.vector_store import get_vector_store, seed_vector_store, similarity_search, get_all
from backend.agent import build_agent, extract_properties_from_output

from dotenv import load_dotenv
# Load variables from .env file
load_dotenv()

CHROMA_DIR = os.path.abspath(os.path.join("db", "chroma_db"))
COLLECTION_NAME = "smartbnb_vector_store"

# ─── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager # Code runs before the application starts up up to yield
async def lifespan(app: FastAPI):
    """Initialise Chroma and seed data on startup."""

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    print("⚙️  Initialising Chroma vector store...")

    store = get_vector_store(api_key)

    # n = seed_vector_store(store, PROPERTIES)
    # if n:
    #     print(f"✅ Seeded {n} properties into Chroma.")
    # else:
    #     print("✅ Chroma already seeded — skipping.")

    # app.state is ageneric container used to store arbitrsry 
    # global data that need to live for the entire lifecycñle

    app.state.vector_store = store # Vector Database (Chroma)
    app.state.openai_api_key = api_key # OpenAI API Key
    app.state.sessions = {}  # session_id → AgentExecutor

    print("🚀 PropSearch API ready.")
    
    # executes after the application finishes handling request and is shutting down
    yield 
    print("👋 Shutting down.")


app = FastAPI(
    title="PropSearch API",
    description="Real-estate search backed by LangChain + Chroma + OpenAI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schemas ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    property_type: Optional[str] = Field(None, description="'Private room in condo' or 'apartment'")
    price: Optional[int] = Field(None, ge=0)
    beds: Optional[int] = Field(None, ge=1)
    k: int = Field(6, ge=1, le=12)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(None, description="Reuse memory across turns; omit to start fresh")
    property_type: Optional[str] = None
    price: Optional[int] = None
    beds: Optional[int] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    properties: list[dict]


class SearchResponse(BaseModel):
    query: str
    total: int
    properties: list[dict]


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"Hello":"World"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "PropSearch API v2"}


@app.get("/properties")
async def list_properties():
    """Return the full list of seeded properties without AI ranking."""
    store = app.state.vector_store
    documents = get_all(store=store)
    return {"total": len(documents["ids"]), "properties": documents} 
    # return {"total": len(PROPERTIES), "properties": PROPERTIES}


@app.post("/search", response_model=SearchResponse)
async def search_properties(req: SearchRequest):
    """
    Pure semantic vector search — no LLM, just embeddings + Chroma.
    Fast, cheap, good for sidebar filter changes.
    """

    filters = {
        "property_type": req.property_type,
        "price": req.price,
        "beds": req.beds,
    }

    try:
        # results = similarity_search(store, req.query, k=req.k, filters=filters)
        results = similarity_search(app.state.vector_store, req.query, k=req.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {e}")
    return {"query": req.query, "total": len(results), "properties": results}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Conversational agent endpoint.
    Creates or reuses a session-scoped AgentExecutor with memory.
    """
    session_id = req.session_id or str(uuid.uuid4())
    sessions = app.state.sessions

    # Create new agent for new sessions
    if session_id not in sessions:
        sessions[session_id] = build_agent(
            app.state.openai_api_key,
            app.state.vector_store,
        )

    agent: object = sessions[session_id]

    # Inject sidebar filter context into user message if provided
    extra = []
    if req.property_type:
        extra.append(f"(filter: {req.property_type}s only)")
    if req.price:
        extra.append(f"(max price: ${req.price:,})")
    if req.beds:
        extra.append(f"(min {req.beds} bedrooms)")
    user_message = req.message
    if extra:
        user_message += "  " + " ".join(extra)

    try:
        result = agent.invoke({"input": user_message})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    raw_output = result.get("output", "")
    reply, properties = extract_properties_from_output(raw_output)

    # If the agent didn't trigger a tool search, fall back to a direct vector search
    if not properties and any(
        kw in req.message.lower()
        for kw in ["find", "search", "show", "looking", "want", "need",
                   "apartment", "house", "bedroom", "budget", "cheap", "luxury"]
    ):
        filters = {
            "type": req.property_type,
            "price": req.price,
            "beds": req.beds,
        }
        properties = similarity_search(app.state.vector_store, req.message, k=6, filters=filters)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        properties=properties,
    )


@app.post("/chat/reset")
async def reset_chat(session_id: str):
    """Clear conversation memory for a given session."""
    sessions = app.state.sessions
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "reset", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/db/status")
async def db_status():
    """Return Chroma collection stats."""
    store = app.state.vector_store
    data = store.get()
    return {
        "collection": COLLECTION_NAME,
        "document_count": len(data.get("ids", [])),
        #"persist_dir": os.path.abspath(
        #    os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        #),
        "persist_dir": CHROMA_DIR
    }

@app.get("/db/test")
async def db_test():
    """Query data from store"""

    store = app.state.vector_store

    results = similarity_search(
        store=store,
        query="university",
        k=10,
    )

    return results # return list of dicts 
