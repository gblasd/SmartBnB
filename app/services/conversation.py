"""Conversation memory management — Layer 1 service.

Manages per-session LangGraph agent executors and conversation history.
Each session stores:
  * A compiled LangGraph agent (StateGraph)
  * A LangChain ConversationBufferWindowMemory instance

Sessions are kept in an in-process dict; swap for Redis/DB in production.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# session_id → {agent, memory}
_sessions: dict[str, dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> dict[str, Any]:
    """
    Return an existing session or create a new one.

    The session dict contains:
      - ``graph``  : compiled LangGraph StateGraph ready to invoke
      - ``memory`` : ConversationBufferWindowMemory
    """
    if session_id not in _sessions:
        # Lazy import to avoid circular dependencies at module load time
        from app.agents.property_search_agent import build_agent

        agent_graph, memory = build_agent()
        _sessions[session_id] = {"agent": agent_graph, "memory": memory}
        logger.info("conversation: created new session %s", session_id)
    return _sessions[session_id]


def clear_session(session_id: str) -> bool:
    """Clear conversation history for a session. Returns True if found."""
    session = _sessions.get(session_id)
    if session is None:
        return False
    try:
        session["memory"].clear()  # InMemoryChatMessageHistory.clear()
    except Exception:
        pass
    del _sessions[session_id]
    logger.info("conversation: cleared session %s", session_id)
    return True


def list_sessions() -> list[str]:
    """Return all active session IDs (for observability)."""
    return list(_sessions.keys())
