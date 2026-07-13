"""Adaptive router — Layer 2 agent.

The adaptive router is the smart traffic controller for the LangGraph
agent.  It decides how to handle each request:

Decision table
--------------
| Condition                            | Action                        |
|--------------------------------------|-------------------------------|
| Query is simple & single-facet       | Direct retrieval (no decomp.) |
| Query is complex / multi-part        | Decompose → multi-retrieval   |
| Query contains unsafe content        | Reject with safety message    |
| Query is off-topic (not real-estate) | Polite redirect               |
| Query matches cache                  | Return cached answer directly |

The router returns a ``RouterDecision`` that tells the LangGraph
StateGraph which edge to follow next.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision enum
# ---------------------------------------------------------------------------

class RouteAction(str, Enum):
    SIMPLE_RETRIEVAL = "simple_retrieval"      # Single-step RAG
    DECOMPOSE = "decompose"                    # Multi-step decomposed RAG
    CACHE_HIT = "cache_hit"                    # Return cached answer
    UNSAFE = "unsafe"                          # Block: unsafe content
    OFF_TOPIC = "off_topic"                    # Redirect: not real-estate


class RouterDecision(BaseModel):
    action: RouteAction = Field(description="The routing action to take.")
    reason: str = Field(description="One-sentence explanation.")


# ---------------------------------------------------------------------------
# Safety & off-topic heuristics (fast, no LLM call)
# ---------------------------------------------------------------------------

_UNSAFE_PATTERNS = re.compile(
    r"\b(hack|exploit|sql injection|drop table|<script|jailbreak|ignore previous)\b",
    re.IGNORECASE,
)
_OFF_TOPIC_PATTERNS = re.compile(
    r"\b(weather|recipe|sport|politics|celebrity|music|movie|joke|poem)\b",
    re.IGNORECASE,
)
_COMPLEX_SIGNALS = re.compile(
    r"(\band\b.*\band\b|\balso\b|\bmoreover\b|\bfurthermore\b|\bmultiple\b|\bboth\b)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# LLM-based routing for ambiguous cases
# ---------------------------------------------------------------------------

_ROUTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a request router for a real-estate AI assistant. "
                "Given a user query, decide the appropriate routing action:\n"
                "- 'simple_retrieval': clear, focused property search query\n"
                "- 'decompose': complex, multi-facet query needing breakdown\n"
                "- 'off_topic': completely unrelated to real estate\n"
                "- 'unsafe': contains harmful or adversarial content\n"
                "Choose the most appropriate action and give a brief reason."
            ),
        ),
        ("human", "User query: {query}"),
    ]
)

_llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.0,
    openai_api_key=settings.OPENAI_API_KEY,
)
_router_chain = _ROUTE_PROMPT | _llm.with_structured_output(RouterDecision)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def adaptive_route(query: str, cache_hit: bool = False) -> RouterDecision:
    """
    Decide how to route an incoming query.

    Parameters
    ----------
    query:
        The (optionally rewritten) user query.
    cache_hit:
        True if the semantic cache already has an answer for this query.

    Returns
    -------
    RouterDecision
    """
    if cache_hit:
        return RouterDecision(
            action=RouteAction.CACHE_HIT,
            reason="Semantic cache hit — returning cached answer.",
        )

    # Fast heuristic checks (no LLM call)
    if _UNSAFE_PATTERNS.search(query):
        logger.warning("adaptive_router: UNSAFE query blocked: %r", query[:80])
        return RouterDecision(
            action=RouteAction.UNSAFE,
            reason="Query contains potentially unsafe content.",
        )

    if _OFF_TOPIC_PATTERNS.search(query):
        return RouterDecision(
            action=RouteAction.OFF_TOPIC,
            reason="Query is not related to real-estate.",
        )

    if _COMPLEX_SIGNALS.search(query) and len(query.split()) > 15:
        return RouterDecision(
            action=RouteAction.DECOMPOSE,
            reason="Query appears complex with multiple requirements.",
        )

    # Fall back to LLM routing for ambiguous cases
    try:
        decision: RouterDecision = _router_chain.invoke({"query": query})
        logger.info(
            "adaptive_router: action=%s (%s) for %r",
            decision.action,
            decision.reason[:60],
            query[:60],
        )
        return decision
    except Exception as exc:  # pragma: no cover
        logger.warning("adaptive_router LLM failed, defaulting to simple_retrieval: %s", exc)
        return RouterDecision(
            action=RouteAction.SIMPLE_RETRIEVAL,
            reason="Router error — defaulting to simple retrieval.",
        )
