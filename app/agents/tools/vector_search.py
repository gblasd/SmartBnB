"""Vector search tool — Layer 2, tools/

Wraps ChromaDB (via LangChain) for semantic / embedding-based retrieval.
Exposes a LangChain @tool callable and a plain helper function so it
can be called both by LangGraph nodes and by the RAG pipeline directly.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool

from app.config import settings

logger = logging.getLogger(__name__)


def _get_chroma() -> Chroma:
    """Instantiate (or re-use) the ChromaDB vector store."""
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDINGS_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            dimensions=256,
        ),
        persist_directory=settings.CHROMA_DB_DIR,
    )


def chroma_search(
    query: str,
    k: int = 6,
    filters: Optional[dict] = None,
) -> list[Document]:
    """
    Run a similarity search against ChromaDB.

    Parameters
    ----------
    query:
        Natural-language search query.
    k:
        Maximum number of documents to retrieve.
    filters:
        Optional ChromaDB metadata filter dict (WHERE clause).

    Returns
    -------
    list[Document]
        Retrieved LangChain Document objects with metadata.
    """
    try:
        store = _get_chroma()
        results = store.similarity_search(query=query, k=k, filter=filters)
        logger.info("vector_search: retrieved %d docs for %r", len(results), query[:60])
        return results
    except Exception as exc:
        logger.error("vector_search failed: %s", exc)
        return []


@tool
def vector_search_tool(query: str, top_k: int = 6) -> str:
    """
    Search the SmartBnB property vector database using semantic similarity.

    Use this tool when the user asks for property recommendations, similar
    listings, or describes what they're looking for in natural language.

    Args:
        query:  Natural-language description of the desired property.
        top_k:  Number of results to return (default 6).

    Returns:
        A formatted text summary of matching properties.
    """
    docs = chroma_search(query, k=top_k)
    if not docs:
        return "No properties found matching your query."
    lines = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        lines.append(
            f"{i}. **{meta.get('property_type', 'Property')}** "
            f"in {meta.get('neighbourhood', '?')}: "
            f"${meta.get('price', '?')}/night, "
            f"{meta.get('bedrooms', '?')} bed / {meta.get('bathrooms', '?')} bath — "
            f"{doc.page_content[:120]}"
        )
    return "\n".join(lines)
