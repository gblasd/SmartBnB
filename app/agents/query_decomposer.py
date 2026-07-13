"""Query decomposer — Layer 2 agent.

Breaks a complex, multi-part user question into a list of focused
sub-queries that are individually answerable by the retrieval system.

Example
-------
Input:  "Show me apartments under $100 in Condesa with at least 2 beds,
         and also tell me which ones have good reviews"
Output: [
    "apartments under $100 in Condesa with 2 bedrooms",
    "listings with good guest reviews in Condesa",
]

This allows the RAG pipeline to retrieve relevant documents for each
facet and produce a more comprehensive, accurate answer.
"""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class DecomposedQueries(BaseModel):
    """List of focused sub-queries derived from a complex user question."""

    sub_queries: list[str] = Field(
        description=(
            "A list of 1–4 focused, self-contained search queries that together "
            "cover all aspects of the original question."
        )
    )


# ---------------------------------------------------------------------------
# Decomposer chain
# ---------------------------------------------------------------------------

_DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a query decomposition specialist for a real-estate AI "
                "assistant. Given a complex user question, break it into a list "
                "of simple, focused sub-queries. Each sub-query should be "
                "independently answerable by a property-search system. "
                "Produce between 1 and 4 sub-queries. "
                "If the question is already simple and focused, return it as-is "
                "in a list of length 1."
            ),
        ),
        (
            "human",
            "Original question: {question}",
        ),
    ]
)

_llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.0,
    openai_api_key=settings.OPENAI_API_KEY,
)

_decomposer_chain = _DECOMPOSE_PROMPT | _llm.with_structured_output(DecomposedQueries)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def decompose_query(question: str) -> list[str]:
    """
    Decompose a question into a list of focused sub-queries.

    Parameters
    ----------
    question:
        The raw or rewritten user question.

    Returns
    -------
    list[str]
        One or more focused sub-queries.  Falls back to ``[question]``
        on any error so the pipeline never fails silently.
    """
    if not question or not question.strip():
        return [question]

    try:
        result: DecomposedQueries = _decomposer_chain.invoke({"question": question})
        sub_queries = [q.strip() for q in result.sub_queries if q.strip()]
        if not sub_queries:
            return [question]
        logger.info(
            "query_decomposer: %d sub-queries for %r → %s",
            len(sub_queries),
            question[:60],
            sub_queries,
        )
        return sub_queries
    except Exception as exc:  # pragma: no cover
        logger.warning("query_decomposer failed, returning original: %s", exc)
        return [question]
