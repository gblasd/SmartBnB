"""Conversation session management."""

from app.agents.property_search_agent import build_agent

sessions = {}

def get_or_create_session(session_id: str, vector_store):
    if session_id not in sessions:
        agent, memory = build_agent(vector_store)
        sessions[session_id] = {"agent": agent, "memory": memory}
    return sessions[session_id]

def clear_session(session_id: str):
    if session_id in sessions:
        sessions[session_id]["memory"].clear()
        return True
    return False
