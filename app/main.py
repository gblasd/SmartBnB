"""FastAPI backend entry point for SmartBnB.

Layer 1 (services/) and Layer 2 (agents/) are wired here via the
LangGraph-powered property search agent and the multi-strategy RAG
pipeline (vector search, BM25, hybrid).
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.database.vector_store import get_vector_store
from app.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SearchRequest,
)
from app.services.conversation import (
    clear_session,
    get_or_create_session,
    list_sessions,
)
from app.services.query_router import RetrievalStrategy
from app.services.rag_pipeline import run_rag_pipeline
from app.agents.property_search_agent import run_agent


# Lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify ChromaDB is accessible."""
    try:
        vs = get_vector_store()
        app.state.vector_store = vs
        print("✅ ChromaDB vector store loaded.")
    except Exception as e:
        app.state.vector_store = None
        print(f"⚠️  ChromaDB init failed: {e}")
    yield


# FastAPI app

app = FastAPI(
    title="SmartBnB API",
    version="0.3.0",
    description=(
        "SmartBnB property search API — powered by LangGraph + LangChain. "
        "Supports vector (ChromaDB), BM25, and hybrid retrieval strategies."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    """Check API and ChromaDB status."""
    vs_ok = app.state.vector_store is not None
    return HealthResponse(
        status="ok",
        vector_store="connected" if vs_ok else "unavailable",
    )


# Properties

@app.get("/properties", tags=["Properties"])
def list_properties():
    """Return raw ChromaDB collection data (all stored properties)."""
    vs = app.state.vector_store
    if vs is None:
        return {"error": "Vector store not initialised"}
    return vs.get()


# Search  (multi-strategy RAG endpoint)

@app.post("/search", tags=["Search"])
def search(
    req: SearchRequest,
    strategy: str = Query(
        default="hybrid",
        description="Retrieval strategy: 'vector', 'bm25', or 'hybrid'",
        regex="^(vector|bm25|hybrid)$",
    ),
):
    """
    Search properties using a natural-language query.

    Supports three retrieval strategies:
    - **vector** — ChromaDB semantic/embedding search
    - **bm25**   — sparse keyword search (BM25Okapi)
    - **hybrid** — combination of both (default)

    The query is automatically rewritten before retrieval.
    """
    try:
        force = RetrievalStrategy(strategy)
    except ValueError:
        force = None  # let the router decide

    result = run_rag_pipeline(
        question=req.query,
        k=req.top_k,
        filters=None,
    )
    return {
        "query": req.query,
        "rewritten": result["rewritten"],
        "strategy": result["strategy"],
        "answer": result["answer"],
        "documents": [
            {**doc.metadata, "content": doc.page_content[:300]}
            for doc in result["documents"]
        ],
    }


# Chat  (LangGraph conversational agent)

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(req: ChatRequest):
    """
    Conversational property search via the LangGraph agent.

    The agent:
    1. Checks the semantic cache
    2. Adaptively routes the query
    3. Decomposes complex queries
    4. Retrieves via vector / BM25 / hybrid
    5. Grades documents for relevance
    6. Generates the final answer
    """
    sid = req.session_id or str(uuid4())
    session = get_or_create_session(sid)
    graph = session["agent"]
    memory = session["memory"]

    result = run_agent(graph=graph, question=req.message, memory=memory)

    answer_text = result.get("answer", "")
    clean_reply = re.sub(
        r"__RESULTS_JSON__.*?__END_JSON__", "", answer_text, flags=re.DOTALL
    ).strip()

    # Serialize documents for the response
    properties = [
        {**doc.metadata, "content": doc.page_content[:300]}
        for doc in result.get("documents", [])
    ] or None

    return ChatResponse(reply=clean_reply, properties=properties, session_id=sid)


@app.post("/chat/reset", tags=["Chat"])
def reset_chat(req: ChatRequest):
    """Clear the conversation history for a given session."""
    sid = req.session_id
    if sid and clear_session(sid):
        return {"status": "cleared", "session_id": sid}
    return {"status": "no session found", "session_id": sid}


# Sessions (observability)

@app.get("/sessions", tags=["System"])
def get_sessions():
    """List all active conversation sessions."""
    return {"sessions": list_sessions()}
