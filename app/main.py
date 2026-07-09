"""FastAPI backend entry point for SmartBnB."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import re

from app.database.vector_store import get_vector_store, similarity_search, get_all
from app.agents.property_search_agent import build_agent, extract_properties_from_output
from app.models import SearchRequest, ChatRequest, ChatResponse
from app.services.conversation import get_or_create_session, clear_session

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        vs = get_vector_store()
        app.state.vector_store = vs
        print("Chroma vector store loaded")
    except Exception as e:
        app.state.vector_store = None
        print(f"Chroma init failed: {e}")
    yield

app = FastAPI(title="SmartBnB API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    vs_ok = app.state.vector_store is not None
    return {"status": "ok", "vector_store": "connected" if vs_ok else "unavailable"}

@app.get("/properties")
def list_properties():
    vs = app.state.vector_store
    if vs is None:
        return {"error": "Vector store not initialised"}
    return get_all(vs)

@app.post("/search")
def search(req: SearchRequest):
    vs = app.state.vector_store
    if vs is None:
        return {"error": "Vector store not initialised"}
    results = similarity_search(vs, req.query, k=req.top_k)
    return {"query": req.query, "results": results}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    vs = app.state.vector_store
    sid = req.session_id or str(uuid4())
    if vs is None:
        return ChatResponse(reply="Vector store is not available.", properties=None, session_id=sid)

    session = get_or_create_session(sid, vs)
    agent_exec = session["agent"]

    try:
        raw = agent_exec.invoke({"input": req.message})
        output_text = raw.get("output", str(raw))
    except Exception as e:
        output_text = f"Sorry, something went wrong: {e}"

    properties = extract_properties_from_output(output_text)
    clean_reply = re.sub(r"__RESULTS_JSON__.*?__END_JSON__", "", output_text, flags=re.DOTALL).strip()
    return ChatResponse(reply=clean_reply, properties=properties, session_id=sid)

@app.post("/chat/reset")
def reset_chat(req: ChatRequest):
    sid = req.session_id
    if sid and clear_session(sid):
        return {"status": "cleared", "session_id": sid}
    return {"status": "no session found", "session_id": sid}
