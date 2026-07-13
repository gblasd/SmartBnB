"""Query rewriter — Layer 1 pre-processing service.

Improves the raw user question before it reaches the retrieval stage,
making it cleaner, more specific, and easier for vector / BM25 search.
"""

from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.prompts.registry import prompt_registry

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.0,
    openai_api_key=settings.OPENAI_API_KEY,
)


def rewrite_query(question: str) -> str:
    """
    Rewrite a raw user query to be more specific and retrieval-friendly.

    Parameters
    ----------
    question:
        The raw query string received from the user.

    Returns
    -------
    str
        The rewritten (improved) query.  Falls back to the original
        question if the LLM call fails.
    """
    if not question or not question.strip():
        return question

    try:
        prompt_template = prompt_registry.get("query_rewrite")
        prompt_text = prompt_template.render(question=question)

        rewritten = _llm.invoke(prompt_text).content.strip()
        logger.info("query_rewriter: %r → %r", question, rewritten)
        return rewritten or question
    except Exception as exc:  # pragma: no cover
        logger.warning("query_rewriter failed, using original: %s", exc)
        return question
