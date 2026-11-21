"""Deterministic source citation resolver (C-CIT, FR-CIT-001 through FR-CIT-007).

Derives structured citation information strictly from the actual document chunks retrieved
and passed to the LLM prompt by querying PostgreSQL document_chunks_meta and documents.
Guarantees zero citation fabrication.
"""

import os
from typing import List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.session import AsyncSessionLocal
from backend.app.db.models import Document, DocumentChunkMeta
from backend.app.rag.vector_store import SearchResult


class Citation(BaseModel):
    """Structured, verified source citation matching actual document metadata."""

    document: str = Field(..., description="Source document filename or title.")
    page: int = Field(..., description="1-indexed source PDF page number.")
    section: Optional[str] = Field(default=None, description="Extracted section heading, if available.")

    model_config = {"extra": "ignore"}


class CitationResolver:
    """Resolves and deduplicates citations from retrieved chunks and PostgreSQL metadata."""

    async def resolve_from_chunk_ids(
        self,
        chunk_ids: List[str],
        session: Optional[AsyncSession] = None,
    ) -> List[Citation]:
        """Resolves citations by mapping vector chunk IDs to document_chunks_meta and documents in PostgreSQL.

        Rules:
        - Never invent or hallucinate citations.
        - Map chunk_id (vector_id) to document_chunks_meta.
        - Retrieve the associated Document master record.
        - Extract document filename and page number.
        - Include section information only when actually extracted.
        - Deduplicate citations for the same source document and page.
        - If metadata is incomplete (missing document name or missing page), omit the citation.

        Args:
            chunk_ids: List of vector_id UUID strings corresponding to chunks used in the prompt.
            session: Optional active AsyncSession. If omitted, opens an isolated session.

        Returns:
            List of verified, deduplicated Citation objects.
        """
        if not chunk_ids:
            return []

        if session is not None:
            return await self._execute_db_resolution(chunk_ids, session)

        async with AsyncSessionLocal() as isolated_session:
            return await self._execute_db_resolution(chunk_ids, isolated_session)

    async def _execute_db_resolution(
        self,
        chunk_ids: List[str],
        session: AsyncSession,
    ) -> List[Citation]:
        """Queries PostgreSQL for chunk metadata joined to the parent document."""
        stmt = (
            select(DocumentChunkMeta, Document)
            .join(Document, DocumentChunkMeta.document_id == Document.id)
            .where(DocumentChunkMeta.vector_id.in_(chunk_ids))
            .order_by(DocumentChunkMeta.chunk_index.asc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        citations: List[Citation] = []
        seen_sources: Set[Tuple[str, int]] = set()

        for chunk_meta, document in rows:
            citation = self._build_citation(
                document_storage_path=document.storage_path,
                document_title=document.title,
                page=chunk_meta.page,
                section=chunk_meta.section,
            )
            if citation is None:
                # Omit incomplete citation
                continue

            dedup_key = (citation.document, citation.page)
            if dedup_key in seen_sources:
                # Avoid duplicate citations for the same source/page
                continue

            seen_sources.add(dedup_key)
            citations.append(citation)

        logger.info(
            "Resolved %d verified citations from %d chunk IDs",
            len(citations),
            len(chunk_ids),
        )
        return citations

    def resolve_from_search_results(
        self,
        chunks: List[SearchResult],
    ) -> List[Citation]:
        """Synchronously resolves and deduplicates citations directly from verified search result payloads.

        Used when database session is unavailable or in offline unit tests.
        """
        if not chunks:
            return []

        citations: List[Citation] = []
        seen_sources: Set[Tuple[str, int]] = set()

        for chunk in chunks:
            citation = self._build_citation(
                document_storage_path=None,
                document_title=chunk.document_name,
                page=chunk.page,
                section=chunk.section,
            )
            if citation is None:
                continue

            dedup_key = (citation.document, citation.page)
            if dedup_key in seen_sources:
                continue

            seen_sources.add(dedup_key)
            citations.append(citation)

        return citations

    def _build_citation(
        self,
        document_storage_path: Optional[str],
        document_title: Optional[str],
        page: Optional[int],
        section: Optional[str],
    ) -> Optional[Citation]:
        """Constructs a Citation object if metadata is complete, otherwise returns None."""
        # 1. Determine document filename or title
        filename: Optional[str] = None
        if document_storage_path:
            raw_filename = os.path.basename(document_storage_path)
            if raw_filename and raw_filename.lower().endswith(".pdf"):
                filename = raw_filename

        if not filename and document_title and document_title.strip():
            filename = document_title.strip()

        # Requirement 9: If metadata is incomplete (missing filename or page), omit it
        if not filename:
            logger.debug("Omitted citation: missing document name/filename")
            return None

        if page is None or page <= 0:
            logger.debug("Omitted citation for '%s': missing or invalid page number (%s)", filename, page)
            return None

        # Requirement 6: Include section information only when actually extracted
        clean_section: Optional[str] = None
        if section and section.strip():
            clean_section = section.strip()

        return Citation(
            document=filename,
            page=page,
            section=clean_section,
        )


citation_resolver = CitationResolver()
