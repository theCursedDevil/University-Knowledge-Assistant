"""Vector retriever with similarity confidence threshold gating (C-RAGSVC, FR-RAG-003, FR-RAG-004, FR-RAG-009).

Retrieves top-k relevant document chunks from Qdrant using cosine similarity,
supports hybrid retrieval combining dense vector similarity with metadata filtering and lexical score fusion,
evaluates retrieval confidence against a configurable threshold, and flags insufficient context.
"""

import re
import uuid
from typing import List, Optional, Set
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.rag.vector_store import vector_store, SearchResult

settings = get_settings()

_STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "and", "or", "but", "if", "then", "else", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now", "what", "which",
}


def compute_lexical_overlap(query: str, text: str) -> float:
    """Computes normalized lexical term overlap between query and chunk text."""
    query_tokens = [
        w.lower() for w in re.findall(r"\b[a-zA-Z0-9_%.-]+\b", query)
        if w.lower() not in _STOPWORDS and len(w) > 1
    ]
    if not query_tokens:
        return 0.0

    text_lower = text.lower()
    matches = sum(1 for token in query_tokens if token in text_lower)
    return round(matches / len(query_tokens), 4)


class RetrievalResult(BaseModel):
    """Encapsulates retrieved chunks and confidence gating evaluation."""

    question: str
    chunks: List[SearchResult] = Field(default_factory=list)
    top_score: float = Field(default=0.0, description="Highest cosine similarity score among retrieved chunks.")
    is_sufficient: bool = Field(default=False, description="True if top_score meets or exceeds confidence threshold.")
    threshold: float = Field(..., description="Configured similarity threshold applied.")
    is_hybrid: bool = Field(default=False, description="True if hybrid lexical-vector fusion was applied.")


class VectorRetriever:
    """Orchestrates top-k cosine similarity retrieval with confidence threshold gating and hybrid score blending."""

    def __init__(self, default_top_k: Optional[int] = None, default_threshold: Optional[float] = None):
        self.default_top_k = default_top_k or settings.RAG_TOP_K
        self.default_threshold = default_threshold or settings.RAG_CONFIDENCE_THRESHOLD

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        filter_category: Optional[str] = None,
        filter_document_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        enable_hybrid: Optional[bool] = None,
        alpha: float = 0.70,
    ) -> RetrievalResult:
        """Embeds natural-language query and searches Qdrant for top-k chunks with role-based visibility.

        Args:
            query: User's question or search query.
            top_k: Number of chunks to retrieve (default: 5).
            confidence_threshold: Minimum similarity score threshold (default: 0.30).
            filter_category: Optional document category filter (e.g. 'Academic', 'Hostel').
            filter_document_id: Optional document ID filter.
            user_role: Optional user role for server-side chunk filtering ('student', 'faculty', 'admin').
            enable_hybrid: Optional flag to toggle hybrid lexical + vector fusion.
            alpha: Dense vector weight in hybrid blending (default: 0.70 vector, 0.30 lexical).

        Returns:
            RetrievalResult containing retrieved chunks, applied threshold, and sufficiency status.
        """
        k = top_k or self.default_top_k
        threshold = confidence_threshold if confidence_threshold is not None else self.default_threshold
        use_hybrid = enable_hybrid if enable_hybrid is not None else settings.RAG_ENABLE_HYBRID_SEARCH

        # If hybrid retrieval is enabled, fetch a slightly larger candidate set for score fusion
        fetch_limit = max(k * 2, 10) if use_hybrid else k

        candidates = vector_store.search(
            query=query,
            limit=fetch_limit,
            score_threshold=None,
            filter_category=filter_category,
            filter_document_id=filter_document_id,
            user_role=user_role,
        )

        if use_hybrid and candidates:
            scored_candidates = []
            for chunk in candidates:
                lex_score = compute_lexical_overlap(query, chunk.chunk_text)
                # Blended hybrid score: alpha * vector_score + (1 - alpha) * lexical_score
                blended_score = round((alpha * chunk.score) + ((1.0 - alpha) * lex_score), 4)
                # Preserve the boosted score on the chunk
                boosted_chunk = chunk.model_copy(update={"score": blended_score})
                scored_candidates.append(boosted_chunk)

            # Re-rank by blended score descending and select final top-k
            scored_candidates.sort(key=lambda c: c.score, reverse=True)
            chunks = scored_candidates[:k]
        else:
            chunks = candidates[:k]

        top_score = chunks[0].score if chunks else 0.0
        # Content is sufficient only if at least one chunk exists and top_score >= threshold
        is_sufficient = bool(chunks) and (top_score >= threshold)

        logger.info(
            "Retrieved %d chunks for query '%s' (top_score=%.4f, threshold=%.4f, hybrid=%s, sufficient=%s)",
            len(chunks),
            query[:60],
            top_score,
            threshold,
            use_hybrid,
            is_sufficient,
        )

        return RetrievalResult(
            question=query,
            chunks=chunks,
            top_score=top_score,
            is_sufficient=is_sufficient,
            threshold=threshold,
            is_hybrid=use_hybrid,
        )


vector_retriever = VectorRetriever()
