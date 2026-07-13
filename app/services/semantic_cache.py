"""Semantic cache — Layer 1 cost-reduction service.

Caches answers for semantically similar questions so the LLM is
not called again for repeat or near-duplicate queries.

Strategy
--------
* Each query is embedded with the same OpenAI embeddings model.
* On a cache hit (cosine similarity ≥ threshold), the cached answer
  is returned immediately — no LLM call needed.
* The cache is in-memory for a single process lifetime.  For
  production, swap the ``_store`` for a Redis or persistent backend.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)

# Cosine similarity threshold: 0 = always miss, 1 = exact match only
_DEFAULT_THRESHOLD: float = 0.92


@dataclass
class CacheEntry:
    query: str
    embedding: list[float]
    answer: str
    hits: int = 0


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class SemanticCache:
    """In-memory semantic cache backed by cosine-similarity lookup."""

    def __init__(self, threshold: float = _DEFAULT_THRESHOLD):
        self._threshold = threshold
        self._store: list[CacheEntry] = []
        self._embedder = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDINGS_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            dimensions=256,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, query: str) -> Optional[str]:
        """Return a cached answer if a semantically similar query exists."""
        if not self._store:
            return None
        try:
            q_emb = self._embedder.embed_query(query)
        except Exception as exc:  # pragma: no cover
            logger.warning("semantic_cache embed failed: %s", exc)
            return None

        best_score = 0.0
        best_entry: Optional[CacheEntry] = None
        for entry in self._store:
            score = _cosine(q_emb, entry.embedding)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= self._threshold:
            best_entry.hits += 1
            logger.info(
                "semantic_cache HIT (score=%.4f, hits=%d) for %r",
                best_score,
                best_entry.hits,
                query[:60],
            )
            return best_entry.answer

        logger.debug("semantic_cache MISS (best_score=%.4f) for %r", best_score, query[:60])
        return None

    def store(self, query: str, answer: str) -> None:
        """Store a new query–answer pair in the cache."""
        try:
            q_emb = self._embedder.embed_query(query)
        except Exception as exc:  # pragma: no cover
            logger.warning("semantic_cache store embed failed: %s", exc)
            return
        self._store.append(CacheEntry(query=query, embedding=q_emb, answer=answer))
        logger.info("semantic_cache stored entry for %r (cache size=%d)", query[:60], len(self._store))

    def clear(self) -> None:
        """Wipe the entire cache."""
        self._store.clear()
        logger.info("semantic_cache cleared")

    @property
    def size(self) -> int:
        return len(self._store)


# Module-level singleton (shared across all requests in a process)
semantic_cache = SemanticCache()
