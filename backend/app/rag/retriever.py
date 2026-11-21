"""Vector retriever with similarity confidence threshold gating (C-RAGSVC, FR-RAG-003, FR-RAG-004).

Retrieves top-k relevant document chunks from Qdrant using cosine similarity,
evaluates retrieval confidence against a configurable threshold, and flags insufficient context.
"""

import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.rag.vector_store import vector_store, SearchResult

settings = get_settings()


class RetrievalResult(BaseModel):
    """Encapsulates retrieved chunks and confidence gating evaluation."""

    question: str
    chunks: List[SearchResult] = Field(default_factory=list)
    top_score: float = Field(default=0.0, description="Highest cosine similarity score among retrieved chunks.")
    is_sufficient: bool = Field(default=False, description="True if top_score meets or exceeds confidence threshold.")
    threshold: float = Field(..., description="Configured similarity threshold applied.")


class VectorRetriever:
    """Orchestrates top-k cosine similarity retrieval with confidence threshold gating."""

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
    ) -> RetrievalResult:
        """Embeds natural-language query and searches Qdrant for top-k chunks.

        Args:
            query: User's question or search query.
            top_k: Number of chunks to retrieve (default: 5).
            confidence_threshold: Minimum cosine similarity score (default: 0.30).
            filter_category: Optional document category filter.
            filter_document_id: Optional document ID filter.

        Returns:
            RetrievalResult containing retrieved chunks and threshold gating status.
        """
        k = top_k or self.default_top_k
        threshold = confidence_threshold if confidence_threshold is not None else self.default_threshold

        chunks = vector_store.search(
            query=query,
            limit=k,
            score_threshold=None,  # We fetch top-k first, then evaluate confidence threshold
            filter_category=filter_category,
            filter_document_id=filter_document_id,
        )

        top_score = chunks[0].score if chunks else 0.0
        # Content is sufficient only if at least one chunk exists and top_score >= threshold
        is_sufficient = bool(chunks) and (top_score >= threshold)

        logger.info(
            "Retrieved %d chunks for query '%s' (top_score=%.4f, threshold=%.4f, sufficient=%s)",
            len(chunks),
            query[:60],
            top_score,
            threshold,
            is_sufficient,
        )

        return RetrievalResult(
            question=query,
            chunks=chunks,
            top_score=top_score,
            is_sufficient=is_sufficient,
            threshold=threshold,
        )


vector_retriever = VectorRetriever()
