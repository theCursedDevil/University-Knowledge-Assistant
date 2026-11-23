"""Groundedness and Hallucination Verification Service (C-RAGSVC, SRS Optional Advanced Enhancement).

Validates whether generated LLM responses are supported by retrieved university context.
Flags, corrects, or replaces ungrounded responses to protect students from hallucinations.
"""

import re
from typing import List, Set
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.rag.vector_store import SearchResult

settings = get_settings()

_COMMON_WORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "and", "or",
    "for", "on", "with", "as", "by", "at", "from", "that", "this", "it", "not",
    "be", "been", "have", "has", "had", "do", "does", "did", "can", "could",
    "should", "would", "will", "shall", "may", "might", "must", "than", "so",
    "source", "based", "according", "university", "policy", "regulations", "documents",
    "provided", "official", "student", "students", "states", "stated", "specifies",
}


class GroundednessReport(BaseModel):
    """Detailed evaluation report on generated answer groundedness."""

    is_grounded: bool = Field(description="True if the response is verified against retrieved chunks.")
    score: float = Field(description="Fraction of factual claims/tokens grounded in context (0.0 to 1.0).")
    threshold: float = Field(description="Groundedness threshold applied.")
    verified_answer: str = Field(description="Original answer if grounded, or safe corrected response if hallucinated.")
    unsupported_claims: List[str] = Field(default_factory=list, description="Extracted claims not found in context.")


class GroundednessChecker:
    """Verifies that generated answers are grounded in retrieved source chunks."""

    def __init__(self, default_threshold: float = 0.50):
        self.default_threshold = default_threshold

    def evaluate(
        self,
        answer: str,
        retrieved_chunks: List[SearchResult],
        threshold: float = 0.50,
    ) -> GroundednessReport:
        """Evaluates whether the generated answer is supported by the context.

        Args:
            answer: Generated LLM response text.
            retrieved_chunks: List of context chunks retrieved for the query.
            threshold: Minimum acceptable groundedness ratio (default: 0.50).

        Returns:
            GroundednessReport containing verification status and safe answer.
        """
        # 1. Honest fallback / insufficient context responses are naturally grounded
        if not retrieved_chunks or settings.RAG_INSUFFICIENT_CONTEXT_MESSAGE in answer or "couldn't find" in answer.lower():
            return GroundednessReport(
                is_grounded=True,
                score=1.0,
                threshold=threshold,
                verified_answer=answer,
                unsupported_claims=[],
            )

        # 2. Build full context corpus
        context_corpus = " ".join(chunk.chunk_text.lower() for chunk in retrieved_chunks)

        # 3. Clean out citation markers like [Source 1] and extract factual tokens: Numbers, percentages, acronyms, and content words
        # E.g. "75%", "6.0", "14", "500", "21:30", "CGPA", "CTC", "LPA"
        cleaned_answer = re.sub(r"\[Source \d+\]", " ", answer)
        answer_tokens = re.findall(r"\b[a-zA-Z0-9_%.:-]+\b", cleaned_answer)
        factual_tokens = [
            t for t in answer_tokens
            if t.lower() not in _COMMON_WORDS and (len(t) > 2 or any(c.isdigit() for c in t))
        ]

        if not factual_tokens:
            return GroundednessReport(
                is_grounded=True,
                score=1.0,
                threshold=threshold,
                verified_answer=answer,
                unsupported_claims=[],
            )

        supported_tokens = []
        unsupported_tokens = []

        for token in factual_tokens:
            token_clean = token.lower().strip(".,;:()")
            if token_clean in context_corpus:
                supported_tokens.append(token)
            else:
                unsupported_tokens.append(token)

        grounded_ratio = round(len(supported_tokens) / len(factual_tokens), 4)
        is_grounded = grounded_ratio >= threshold

        logger.info(
            "Groundedness check: ratio=%.4f (threshold=%.2f, supported=%d, unsupported=%d, grounded=%s)",
            grounded_ratio,
            threshold,
            len(supported_tokens),
            len(unsupported_tokens),
            is_grounded,
        )

        if is_grounded:
            final_answer = answer
        else:
            final_answer = (
                "I could not fully verify that all statements in this response are supported by official "
                "university documents. Please consult the cited source documents directly.\n\n"
                "[Unverified statements omitted for academic accuracy]."
            )

        return GroundednessReport(
            is_grounded=is_grounded,
            score=grounded_ratio,
            threshold=threshold,
            verified_answer=final_answer,
            unsupported_claims=unsupported_tokens[:5],
        )


groundedness_checker = GroundednessChecker()
