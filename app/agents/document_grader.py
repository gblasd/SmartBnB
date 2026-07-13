"""Document grader — Layer 2 agent.

Evaluates retrieved documents for relevance to a user query before they
are passed to the answer-generation LLM.  Irrelevant documents are
filtered out so the final answer is grounded in useful context.

Implements a lightweight LangChain chain:
    prompt → LLM (structured output) → binary relevance score
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class GradeScore(BaseModel):
    """Binary relevance score for a retrieved document."""

    score: Literal["yes", "no"] = Field(
        description="'yes' if the document is relevant to the question, 'no' otherwise."
    )
    reasoning: str = Field(
        description="One-sentence explanation for the grade."
    )


# ---------------------------------------------------------------------------
# Grader chain
# ---------------------------------------------------------------------------

_GRADE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a relevance grader for a real-estate AI assistant. "
                "Given a user question and a retrieved document, decide whether "
                "the document contains information that is useful for answering "
                "the question. Be strict — only grade 'yes' if the document is "
                "clearly relevant."
            ),
        ),
        (
            "human",
            (
                "Question: {question}\n\n"
                "Document:\n{document}\n\n"
                "Is this document relevant?"
            ),
        ),
    ]
)

_llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.0,
    openai_api_key=settings.OPENAI_API_KEY,
)

_grader_chain = _GRADE_PROMPT | _llm.with_structured_output(GradeScore)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def grade_document(question: str, document: Document) -> GradeScore:
    """
    Grade a single document against a question.

    Parameters
    ----------
    question:
        The user's (rewritten) query.
    document:
        A retrieved LangChain Document.

    Returns
    -------
    GradeScore with ``score`` == "yes" | "no"
    """
    try:
        result: GradeScore = _grader_chain.invoke(
            {"question": question, "document": document.page_content[:600]}
        )
        logger.debug(
            "document_grader: score=%s (%s)", result.score, result.reasoning[:80]
        )
        return result
    except Exception as exc:  # pragma: no cover
        logger.warning("document_grader failed, defaulting to 'yes': %s", exc)
        return GradeScore(score="yes", reasoning="grader error — keeping document")


def filter_relevant(
    question: str,
    documents: list[Document],
) -> list[Document]:
    """
    Return only the documents that are graded as relevant.

    Parameters
    ----------
    question:
        The user query used for grading.
    documents:
        Candidate documents from retrieval.

    Returns
    -------
    list[Document]
        Filtered list containing only relevant documents.
    """
    relevant = []
    for doc in documents:
        grade = grade_document(question, doc)
        if grade.score == "yes":
            relevant.append(doc)
    logger.info(
        "document_grader: %d / %d documents kept for %r",
        len(relevant),
        len(documents),
        question[:60],
    )
    return relevant
