"""RAG pipeline — Layer 1 brain of the SmartBnB AI system.

Flow
----
1. Rewrite the raw user query (query_rewriter).
2. Route to the correct retrieval strategy (query_router).
3. Retrieve documents (ChromaDB vector search or BM25).
4. Grade retrieved documents for relevance (document_grader agent).
5. Generate the final answer with the LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.registry import prompt_registry
from app.services.query_rewriter import rewrite_query
from app.services.query_router import route_query, RetrievalStrategy
from app.agents.tools.vector_search import chroma_search
from app.agents.tools.bm25_search import bm25_search

logger = logging.getLogger(__name__)


def _format_docs(docs: list[Document]) -> str:
    """Concatenate document page contents for the LLM context window."""
    if not docs:
        return "No relevant properties found."
    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        parts.append(
            f"[{i}] {meta.get('property_type', 'Property')} in "
            f"{meta.get('neighbourhood', '?')} — "
            f"${meta.get('price', '?')}/night, "
            f"{meta.get('bedrooms', '?')} bed / {meta.get('bathrooms', '?')} bath\n"
            f"{doc.page_content[:300]}"
        )
    return "\n\n".join(parts)


def _retrieve(
    query: str,
    strategy: RetrievalStrategy,
    k: int = 6,
    filters: dict | None = None,
) -> list[Document]:
    """Dispatch retrieval to the correct backend."""
    if strategy == RetrievalStrategy.VECTOR:
        logger.info("RAG: using vector (Chroma) retrieval for query=%r", query)
        return chroma_search(query, k=k, filters=filters)
    elif strategy == RetrievalStrategy.BM25:
        logger.info("RAG: using BM25 retrieval for query=%r", query)
        return bm25_search(query, k=k)
    else:  # HYBRID
        logger.info("RAG: using hybrid retrieval for query=%r", query)
        vec_docs = chroma_search(query, k=k, filters=filters)
        bm25_docs = bm25_search(query, k=k)
        # Deduplicate by page_content
        seen: set[str] = set()
        merged: list[Document] = []
        for doc in vec_docs + bm25_docs:
            key = doc.page_content[:120]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged[:k]


def run_rag_pipeline(
    question: str,
    k: int = 6,
    filters: dict | None = None,
) -> dict[str, Any]:
    """
    Execute the full RAG pipeline for a property-search question.

    Returns
    -------
    dict with keys:
        answer      - the LLM-generated answer string
        documents   - list of retrieved Document objects
        strategy    - the RetrievalStrategy that was chosen
        rewritten   - the rewritten query string
    """
    # 1. Rewrite
    rewritten = rewrite_query(question)
    logger.info("RAG: rewritten query=%r", rewritten)

    # 2. Route
    strategy = route_query(rewritten)

    # 3. Retrieve
    docs = _retrieve(rewritten, strategy, k=k, filters=filters)

    # 4. Build context and call LLM
    context = _format_docs(docs)
    prompt_template = prompt_registry.get("property_search")
    prompt_text = prompt_template.render(context=context, question=rewritten)

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    answer = llm.invoke(prompt_text).content

    return {
        "answer": answer,
        "documents": docs,
        "strategy": strategy.value,
        "rewritten": rewritten,
    }
