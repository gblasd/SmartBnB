"""Query router — Layer 1 routing service.

Decides which retrieval strategy to use for each incoming query:

* VECTOR  — pure semantic / embedding-based search via ChromaDB
* BM25    — sparse keyword retrieval via BM25
* HYBRID  — combine both (default for ambiguous queries)

The routing decision is heuristic-first (keyword signals) and can be
overridden at call time by the caller if a specific strategy is forced.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class RetrievalStrategy(str, Enum):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


# Keywords that strongly suggest exact / keyword-heavy queries (→ BM25)
_BM25_SIGNALS: list[str] = [
    r"\b(exact|exactly)\b",
    r"\b(listing[_ ]?id|id\s*[:=]\s*\d+)\b",
    r"\b(code|reference|sku|ref)\b",
    r"\baddress\b",
    r"\bneighbourhood\b",
    r"\bcolonia\b",
    r"\"[^\"]+\"",   # quoted phrases
]

# Keywords that strongly suggest semantic / conceptual queries (→ VECTOR)
_VECTOR_SIGNALS: list[str] = [
    r"\b(similar|like|cozy|comfortable|luxurious|charming|modern)\b",
    r"\b(feel|vibe|atmosphere|style)\b",
    r"\b(recommend|suggest|find me)\b",
    r"\b(best|top|most)\b",
]

_BM25_RE = re.compile("|".join(_BM25_SIGNALS), re.IGNORECASE)
_VECTOR_RE = re.compile("|".join(_VECTOR_SIGNALS), re.IGNORECASE)


def route_query(
    query: str,
    force: RetrievalStrategy | None = None,
) -> RetrievalStrategy:
    """
    Choose a retrieval strategy for the given query.

    Parameters
    ----------
    query:
        The (optionally rewritten) user query.
    force:
        Override the automatic decision with a specific strategy.

    Returns
    -------
    RetrievalStrategy
    """
    if force is not None:
        logger.info("query_router: strategy forced to %s", force.value)
        return force

    has_bm25 = bool(_BM25_RE.search(query))
    has_vector = bool(_VECTOR_RE.search(query))

    if has_bm25 and not has_vector:
        strategy = RetrievalStrategy.BM25
    elif has_vector and not has_bm25:
        strategy = RetrievalStrategy.VECTOR
    else:
        # Default to hybrid when signals are mixed or absent
        strategy = RetrievalStrategy.HYBRID

    logger.info("query_router: query=%r → strategy=%s", query[:80], strategy.value)
    return strategy
