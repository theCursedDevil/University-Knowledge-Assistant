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
        """Conservatively checks exact terms and numeric facts against retrieved text.

        This is a deterministic heuristic, not a semantic entailment model. Exact numeric
        mismatches are rejected even when the remaining vocabulary overlap is high.
        """
        normalized_answer = answer.strip()
        fallback = settings.RAG_INSUFFICIENT_CONTEXT_MESSAGE.strip()
        if normalized_answer == fallback:
            return GroundednessReport(
                is_grounded=True,
                score=1.0,
                threshold=threshold,
                verified_answer=answer,
                unsupported_claims=[],
            )
        if not retrieved_chunks:
            return GroundednessReport(
                is_grounded=False,
                score=0.0,
                threshold=threshold,
                verified_answer=(
                    "I could not verify this response against available university documents. "
                    "Please consult the source documents directly."
                ),
                unsupported_claims=["No retrieved source context"],
            )

        context = " ".join(chunk.chunk_text.lower() for chunk in retrieved_chunks)
        cleaned_answer = re.sub(r"\[Source\s+\d+\]", " ", answer, flags=re.IGNORECASE)

        def words(value: str) -> Set[str]:
            return {
                token.lower()
                for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*|\d+(?:\.\d+)?", value)
                if token.lower() not in _COMMON_WORDS
                and (len(token) > 2 or any(char.isdigit() for char in token))
            }

        answer_tokens = words(cleaned_answer)
        context_tokens = words(context)
        if not answer_tokens:
            return GroundednessReport(
                is_grounded=True,
                score=1.0,
                threshold=threshold,
                verified_answer=answer,
                unsupported_claims=[],
            )

        unsupported_tokens = sorted(answer_tokens - context_tokens)
        grounded_ratio = round((len(answer_tokens) - len(unsupported_tokens)) / len(answer_tokens), 4)

        # Keep numeric value + unit/currency together. A mention of 5% must not be
        # supported by 75%, and Rs 1,750 must not be supported by Rs 175,000.
        numeric_pattern = re.compile(
            r"(?<![\w])(?P<currency>rs\.?|inr|₹)?\s*"
            r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
            r"(?P<unit>%|percent|lpa|lakhs?|crore|cr|years?|months?|days?)?",
            re.IGNORECASE,
        )

        def numeric_facts(value: str) -> Set[tuple[str, str, str]]:
            facts: Set[tuple[str, str, str]] = set()
            for match in numeric_pattern.finditer(value):
                raw_number = match.group("number").replace(",", "")
                try:
                    number = str(float(raw_number)).rstrip("0").rstrip(".")
                except ValueError:
                    continue
                currency = (match.group("currency") or "").lower().replace(".", "")
                if currency in ("rs", "inr", "₹"):
                    currency = "inr"
                unit = (match.group("unit") or "").lower()
                if unit == "percent":
                    unit = "%"
                facts.add((currency, number, unit))
            return facts

        context_numbers = numeric_facts(context)
        answer_numbers = numeric_facts(cleaned_answer)
        unsupported_numbers = sorted(answer_numbers - context_numbers)
        is_grounded = grounded_ratio >= threshold and not unsupported_numbers

        unsupported_claims = unsupported_tokens[:5]
        unsupported_claims.extend(
            f"unsupported numeric fact: {' '.join(part for part in fact if part)}"
            for fact in unsupported_numbers[:5]
        )

        logger.info(
            "Groundedness check: ratio=%.4f (threshold=%.2f, unsupported_terms=%d, unsupported_numbers=%d, grounded=%s)",
            grounded_ratio,
            threshold,
            len(unsupported_tokens),
            len(unsupported_numbers),
            is_grounded,
        )

        if is_grounded:
            final_answer = answer
        else:
            final_answer = (
                "I could not fully verify that this response is supported by the retrieved university documents. "
                "Please consult the cited source documents directly.\n\n"
                "[Unverified response omitted for academic accuracy]."
            )

        return GroundednessReport(
            is_grounded=is_grounded,
            score=grounded_ratio if not unsupported_numbers else min(grounded_ratio, 0.0),
            threshold=threshold,
            verified_answer=final_answer,
            unsupported_claims=unsupported_claims,
        )



groundedness_checker = GroundednessChecker()
