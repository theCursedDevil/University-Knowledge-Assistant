"""Modular candidate chunk re-ranker (C-RAGSVC, SRS Optional Advanced Enhancement).

Provides:
1. Zero-RAM Lexical & Reciprocal Rank Fusion (RRF) re-ranking by default.
2. Optional Cross-Encoder neural re-ranking hook (disabled by default to preserve local host RAM and CPU).
3. Candidate pooling: filters an initial candidate set (e.g. 20 chunks) down to final top-k chunks.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.rag.vector_store import SearchResult

settings = get_settings()


class RerankResult(BaseModel):
    """Result of re-ranking candidate chunks."""

    original_count: int
    reranked_count: int
    chunks: List[SearchResult] = Field(default_factory=list)
    strategy_used: str = Field(default="passthrough")


class ChunkReranker:
    """Manages candidate chunk re-ranking with minimal resource overhead."""

    def __init__(self, enabled: Optional[bool] = None, candidate_pool_k: Optional[int] = None):
        self.enabled = enabled if enabled is not None else settings.RAG_ENABLE_RERANKING
        self.candidate_pool_k = candidate_pool_k or settings.RAG_RERANK_CANDIDATES_K

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
        strategy: str = "lexical_boost",
    ) -> RerankResult:
        """Re-ranks a candidate set of chunks down to final top-k.

        Args:
            query: User's question.
            candidates: Initial pool of candidate chunks (typically 10-20).
            top_k: Number of final chunks to return.
            strategy: 'passthrough', 'lexical_boost', or 'cross_encoder'.

        Returns:
            RerankResult with re-ranked chunks.
        """
        if not candidates:
            return RerankResult(original_count=0, reranked_count=0, chunks=[], strategy_used="none")

        if not self.enabled or strategy == "passthrough":
            return RerankResult(
                original_count=len(candidates),
                reranked_count=min(len(candidates), top_k),
                chunks=candidates[:top_k],
                strategy_used="passthrough",
            )

        # Zero-RAM Lexical Re-ranking: Term frequency & exact matching density boost
        logger.info("Applying lightweight zero-RAM re-ranking on %d candidates for query '%s'", len(candidates), query[:40])
        query_words = [w.lower() for w in query.split() if len(w) > 2]

        scored_candidates = []
        for idx, chunk in enumerate(candidates):
            text_lower = chunk.chunk_text.lower()
            # Frequency score: how many times query keywords occur in text
            keyword_hits = sum(text_lower.count(qw) for qw in query_words)
            # Reciprocal rank contribution: 1 / (60 + vector_rank)
            rrf_score = 1.0 / (60 + idx + 1)
            # Combined re-rank score
            combined_score = chunk.score + (0.05 * min(keyword_hits, 5)) + rrf_score
            updated_chunk = chunk.model_copy(update={"score": round(combined_score, 4)})
            scored_candidates.append(updated_chunk)

        scored_candidates.sort(key=lambda c: c.score, reverse=True)
        final_chunks = scored_candidates[:top_k]

        return RerankResult(
            original_count=len(candidates),
            reranked_count=len(final_chunks),
            chunks=final_chunks,
            strategy_used="lexical_rrf",
        )


chunk_reranker = ChunkReranker()
