"""BM25 search tool — Layer 2, tools/

Implements sparse keyword retrieval using the BM25Okapi algorithm.
The corpus is loaded lazily from ChromaDB on first call so the index
always reflects the current state of the vector store.

Architecture note
-----------------
BM25 is a complementary retrieval method to dense vector search.
It excels at exact-term matching (property names, IDs, neighbourhoods)
while vector search excels at semantic / conceptual queries.
Together they form the hybrid retrieval strategy used by the RAG pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BM25 corpus cache — rebuilt when the Chroma collection changes
# ---------------------------------------------------------------------------
_corpus_docs: list[Document] = []
_bm25_index: Optional[object] = None  # rank_bm25.BM25Okapi


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


def _build_index() -> None:
    """Load all documents from ChromaDB and build the BM25 index."""
    global _corpus_docs, _bm25_index

    try:
        from rank_bm25 import BM25Okapi  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "rank-bm25 is required for BM25 retrieval. "
            "Install it with: pip install rank-bm25"
        ) from exc

    store = Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDINGS_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            dimensions=256,
        ),
        persist_directory=settings.CHROMA_DB_DIR,
    )
    raw = store.get(include=["documents", "metadatas"])
    _corpus_docs = []
    for content, meta in zip(raw.get("documents", []), raw.get("metadatas", [])):
        _corpus_docs.append(Document(page_content=content or "", metadata=meta or {}))

    if not _corpus_docs:
        logger.warning("bm25_search: corpus is empty, index not built")
        _bm25_index = None
        return

    tokenized = [_tokenize(doc.page_content) for doc in _corpus_docs]
    _bm25_index = BM25Okapi(tokenized)
    logger.info("bm25_search: index built with %d documents", len(_corpus_docs))


def bm25_search(
    query: str,
    k: int = 6,
    rebuild: bool = False,
) -> list[Document]:
    """
    Run a BM25 keyword search over the property corpus.

    Parameters
    ----------
    query:
        The search query string.
    k:
        Maximum number of documents to return.
    rebuild:
        Force a rebuild of the BM25 index from ChromaDB.

    Returns
    -------
    list[Document]
    """
    global _bm25_index

    if _bm25_index is None or rebuild:
        _build_index()

    if _bm25_index is None:
        logger.warning("bm25_search: index unavailable, returning empty")
        return []

    tokens = _tokenize(query)
    scores = _bm25_index.get_scores(tokens)

    # Pair with documents and sort descending by score
    ranked = sorted(
        enumerate(scores),
        key=lambda x: x[1],
        reverse=True,
    )
    top_k = [_corpus_docs[i] for i, score in ranked[:k] if score > 0]
    logger.info("bm25_search: returned %d docs for %r", len(top_k), query[:60])
    return top_k


@tool
def bm25_search_tool(query: str, top_k: int = 6) -> str:
    """
    Search the SmartBnB property database using BM25 keyword matching.

    Use this tool when the user mentions exact terms, neighbourhood names,
    listing IDs, property codes, or other specific keywords.

    Args:
        query:  Keyword-focused search query.
        top_k:  Number of results to return (default 6).

    Returns:
        A formatted text summary of matching properties.
    """
    docs = bm25_search(query, k=top_k)
    if not docs:
        return "No properties found matching your keywords."
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
