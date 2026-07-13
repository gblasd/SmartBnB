"""Property search agent — Layer 2 (LangGraph).

Implements a multi-node StateGraph that orchestrates:

  1. adaptive_route  → decide how to handle the query
  2. rewrite_node    → query rewriting
  3. retrieve_node   → multi-strategy retrieval (vector / BM25 / hybrid)
  4. grade_node      → document relevance grading
  5. generate_node   → answer generation with the LLM
  6. decompose_node  → break complex queries into sub-queries (conditional)

State schema
------------
AgentState is a TypedDict that flows through every node.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Annotated, Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.config import settings
from app.prompts.registry import prompt_registry
from app.agents.adaptive_router import RouteAction, adaptive_route
from app.agents.document_grader import filter_relevant
from app.agents.query_decomposer import decompose_query
from app.agents.tools.vector_search import chroma_search
from app.agents.tools.bm25_search import bm25_search
from app.services.query_rewriter import rewrite_query
from app.services.query_router import RetrievalStrategy, route_query
from app.services.semantic_cache import semantic_cache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Mutable state that flows through every node of the LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    rewritten: str
    sub_queries: list[str]
    documents: list[Document]
    answer: str
    strategy: str
    route_action: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def route_node(state: AgentState) -> AgentState:
    """Decide how to handle the query (adaptive router)."""
    question = state["question"]

    # Check semantic cache first
    cached = semantic_cache.lookup(question)
    cache_hit = cached is not None

    decision = adaptive_route(question, cache_hit=cache_hit)
    logger.info("route_node: action=%s", decision.action)

    updates: dict[str, Any] = {"route_action": decision.action}
    if cache_hit and decision.action == RouteAction.CACHE_HIT:
        updates["answer"] = cached  # type: ignore[assignment]

    return {**state, **updates}


def rewrite_node(state: AgentState) -> AgentState:
    """Rewrite the query for better retrieval performance."""
    rewritten = rewrite_query(state["question"])
    return {**state, "rewritten": rewritten}


def decompose_node(state: AgentState) -> AgentState:
    """Break a complex query into focused sub-queries."""
    sub_queries = decompose_query(state.get("rewritten") or state["question"])
    return {**state, "sub_queries": sub_queries}


def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve documents using the router-selected strategy."""
    query = state.get("rewritten") or state["question"]
    sub_queries = state.get("sub_queries") or [query]
    strategy = route_query(query)

    all_docs: list[Document] = []
    seen_keys: set[str] = set()

    for sq in sub_queries:
        if strategy == RetrievalStrategy.BM25:
            docs = bm25_search(sq, k=6)
        elif strategy == RetrievalStrategy.VECTOR:
            docs = chroma_search(sq, k=6)
        else:  # HYBRID
            vec_docs = chroma_search(sq, k=4)
            bm_docs = bm25_search(sq, k=4)
            docs = vec_docs + bm_docs

        for doc in docs:
            key = doc.page_content[:120]
            if key not in seen_keys:
                seen_keys.add(key)
                all_docs.append(doc)

    logger.info(
        "retrieve_node: retrieved %d docs (strategy=%s) for %r",
        len(all_docs),
        strategy.value,
        query[:60],
    )
    return {**state, "documents": all_docs[:10], "strategy": strategy.value}


def grade_node(state: AgentState) -> AgentState:
    """Filter retrieved documents to only relevant ones."""
    question = state.get("rewritten") or state["question"]
    docs = state.get("documents", [])
    relevant = filter_relevant(question, docs)
    return {**state, "documents": relevant}


def generate_node(state: AgentState) -> AgentState:
    """Generate the final answer with the LLM."""
    question = state.get("rewritten") or state["question"]
    docs = state.get("documents", [])

    if not docs:
        context = "No relevant properties were found."
    else:
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            parts.append(
                f"[{i}] {meta.get('property_type', 'Property')} "
                f"in {meta.get('neighbourhood', '?')}: "
                f"${meta.get('price', '?')}/night, "
                f"{meta.get('bedrooms', '?')} bed / {meta.get('bathrooms', '?')} bath\n"
                f"{doc.page_content[:300]}"
            )
        context = "\n\n".join(parts)

    prompt_template = prompt_registry.get("property_search")
    prompt_text = prompt_template.render(context=context, question=question)

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    answer = llm.invoke(prompt_text).content

    # Store in semantic cache for future identical queries
    semantic_cache.store(state["question"], answer)

    return {
        **state,
        "answer": answer,
        "messages": state["messages"] + [AIMessage(content=answer)],
    }


def safety_node(state: AgentState) -> AgentState:
    """Return a safety rejection message."""
    msg = "I'm sorry, but I can't process that request. Please ask me about properties."
    return {
        **state,
        "answer": msg,
        "messages": state["messages"] + [AIMessage(content=msg)],
    }


def off_topic_node(state: AgentState) -> AgentState:
    """Return a polite redirect for off-topic queries."""
    msg = (
        "I'm PropBot, a real-estate assistant specialising in SmartBnB properties. "
        "I can help you find apartments, houses, or rooms to rent. "
        "Feel free to ask about any properties!"
    )
    return {
        **state,
        "answer": msg,
        "messages": state["messages"] + [AIMessage(content=msg)],
    }


# ---------------------------------------------------------------------------
# Conditional edge helpers
# ---------------------------------------------------------------------------

def _route_edge(state: AgentState) -> str:
    action = state.get("route_action", "")
    if action == RouteAction.CACHE_HIT:
        return "cache_hit"
    if action == RouteAction.UNSAFE:
        return "unsafe"
    if action == RouteAction.OFF_TOPIC:
        return "off_topic"
    if action == RouteAction.DECOMPOSE:
        return "decompose"
    return "simple"


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------

def _build_graph() -> Any:
    """Compile the LangGraph StateGraph for the property search agent."""
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("route", route_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("decompose", decompose_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_node)
    graph.add_node("generate", generate_node)
    graph.add_node("safety", safety_node)
    graph.add_node("off_topic", off_topic_node)

    # Entry point
    graph.set_entry_point("route")

    # Conditional edges from route
    graph.add_conditional_edges(
        "route",
        _route_edge,
        {
            "cache_hit": END,         # Answer already in state
            "unsafe": "safety",
            "off_topic": "off_topic",
            "decompose": "decompose",
            "simple": "rewrite",
        },
    )

    # Linear path for simple queries
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_edge("grade", "generate")
    graph.add_edge("generate", END)

    # Decompose path
    graph.add_edge("decompose", "retrieve")

    # Terminal nodes
    graph.add_edge("safety", END)
    graph.add_edge("off_topic", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_agent():
    """
    Build and return a compiled LangGraph agent + chat history object.

    Returns
    -------
    tuple[CompiledGraph, InMemoryChatMessageHistory]
    """
    memory = InMemoryChatMessageHistory()
    graph = _build_graph()
    return graph, memory


def run_agent(
    graph: Any,
    question: str,
    memory: InMemoryChatMessageHistory,
) -> dict[str, Any]:
    """
    Run the compiled LangGraph agent for a single question.

    Parameters
    ----------
    graph:
        The compiled LangGraph (from build_agent).
    question:
        The user's raw question.
    memory:
        InMemoryChatMessageHistory holding the conversation so far.

    Returns
    -------
    dict with keys: answer, documents, strategy, rewritten
    """
    history: list[BaseMessage] = memory.messages[-20:]  # last 20 messages (10 turns)

    initial_state: AgentState = {
        "messages": list(history) + [HumanMessage(content=question)],
        "question": question,
        "rewritten": "",
        "sub_queries": [],
        "documents": [],
        "answer": "",
        "strategy": "",
        "route_action": "",
        "metadata": {},
    }

    final_state = graph.invoke(initial_state)
    answer = final_state.get("answer", "")

    # Persist to memory
    memory.add_user_message(question)
    memory.add_ai_message(answer)

    return {
        "answer": answer,
        "documents": final_state.get("documents", []),
        "strategy": final_state.get("strategy", ""),
        "rewritten": final_state.get("rewritten", question),
    }


# ---------------------------------------------------------------------------
# Backward-compat helper (used by conversation.py)
# ---------------------------------------------------------------------------

def extract_properties_from_output(text: str) -> list[dict] | None:
    """Extract a JSON block from the LLM output if present (legacy support)."""
    match = re.search(r"__RESULTS_JSON__(.*?)__END_JSON__", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
