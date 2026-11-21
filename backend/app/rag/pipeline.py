"""Document ingestion pipeline orchestrating extraction, chunking, embedding, and indexing (C-PROC).

Lifecycle:
PDF upload -> text extraction (PyMuPDF) -> text cleaning -> chunking (LangChain)
-> metadata extraction -> embedding generation (Sentence Transformers)
-> vector storage (Qdrant) -> chunk metadata persistence (PostgreSQL).

Status transitions:
processing -> ready (on complete success)
processing -> failed (on any extraction, chunking, embedding, or indexing failure)
"""

import uuid
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.core.errors import NotFoundError, ValidationError, AppException
from backend.app.db.session import AsyncSessionLocal
from backend.app.db.models import Document, DocumentChunkMeta, AuditLog
from backend.app.services.storage import storage_service
from backend.app.rag.extractor import extract_text_from_pdf
from backend.app.rag.chunker import chunk_document_pages
from backend.app.rag.embeddings import embedding_client
from backend.app.rag.vector_store import vector_store


class ProcessingResult(BaseModel):
    """Result summary of a document processing pipeline run."""

    document_id: uuid.UUID
    status: str = Field(..., description="Final processing status: 'ready' or 'failed'.")
    pages_count: int = Field(default=0, description="Total pages successfully extracted.")
    chunks_count: int = Field(default=0, description="Total chunks indexed into vector store.")
    error: Optional[str] = Field(default=None, description="Error message if processing failed.")


async def process_document(
    document_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> ProcessingResult:
    """Executes the end-to-end ingestion pipeline for a stored document.

    If session is not provided, manages an isolated database session.
    Guarantees atomic status updates and cleans up any partial vectors on failure.

    Args:
        document_id: UUID of the document record in PostgreSQL.
        session: Optional external AsyncSession (used in tests or transaction wrappers).

    Returns:
        ProcessingResult with final status ('ready' or 'failed') and indexing stats.
    """
    if session is not None:
        return await _execute_pipeline(document_id, session)

    async with AsyncSessionLocal() as isolated_session:
        return await _execute_pipeline(document_id, isolated_session)


async def _execute_pipeline(
    document_id: uuid.UUID,
    db: AsyncSession,
) -> ProcessingResult:
    """Internal pipeline execution logic."""
    # 1. Fetch document record
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        logger.error("Document not found for processing: %s", document_id)
        raise NotFoundError(
            message=f"Document with ID '{document_id}' not found.",
            details={"document_id": str(document_id)},
        )

    # 2. Mark status as processing
    document.status = "processing"
    await db.commit()
    await db.refresh(document)
    logger.info("Starting ingestion pipeline for document '%s' (title: '%s')", document_id, document.title)

    try:
        # 3. Retrieve raw PDF bytes from MinIO
        if not storage_service.file_exists(document.storage_path):
            raise AppException(
                message=f"Storage object '{document.storage_path}' not found in MinIO.",
                code="STORAGE_OBJECT_NOT_FOUND",
            )
        pdf_bytes = storage_service.get_file(document.storage_path)

        # 4. Extract text page-by-page (PyMuPDF)
        extracted_pages = extract_text_from_pdf(pdf_bytes)
        if not extracted_pages:
            raise ValidationError("No extractable text found in PDF document.")

        # 5. Semantic chunking (LangChain RecursiveCharacterTextSplitter)
        chunks = chunk_document_pages(extracted_pages)
        if not chunks:
            raise ValidationError("Document produced 0 text chunks during segmentation.")

        # 6. Generate dense vector embeddings (Sentence Transformers all-MiniLM-L6-v2)
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedding_client.embed_texts(chunk_texts)

        # 7. Index vectors into Qdrant (remove prior vectors if re-processing)
        vector_store.delete_document_vectors(document_id)
        vector_ids = vector_store.upsert_chunks(
            document_id=document.id,
            document_title=document.title,
            category=document.category,
            chunks=chunks,
            embeddings=embeddings,
        )

        # 8. Clean up prior chunk metadata in PostgreSQL (for re-runs)
        await db.execute(
            delete(DocumentChunkMeta).where(DocumentChunkMeta.document_id == document_id)
        )

        # 9. Persist chunk metadata in PostgreSQL
        for chunk, vector_id in zip(chunks, vector_ids):
            chunk_record = DocumentChunkMeta(
                id=uuid.uuid4(),
                vector_id=vector_id,
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                section=chunk.section,
            )
            db.add(chunk_record)

        # 10. Update status to 'ready'
        document.status = "ready"

        # 11. Audit log
        audit_entry = AuditLog(
            user_id=document.uploaded_by,
            action="DOCUMENT_PROCESSED",
            entity="documents",
            entity_id=str(document_id),
            details={
                "title": document.title,
                "category": document.category,
                "pages_count": len(extracted_pages),
                "chunks_count": len(chunks),
                "status": "ready",
            },
        )
        db.add(audit_entry)

        await db.commit()
        await db.refresh(document)

        logger.info(
            "Document '%s' successfully processed: %d pages, %d chunks indexed.",
            document_id,
            len(extracted_pages),
            len(chunks),
        )

        return ProcessingResult(
            document_id=document_id,
            status="ready",
            pages_count=len(extracted_pages),
            chunks_count=len(chunks),
        )

    except Exception as exc:
        logger.error("Document processing failed for '%s': %s", document_id, exc, exc_info=True)
        # Rollback partial database changes
        await db.rollback()

        # Clean up any partial vectors in Qdrant
        try:
            vector_store.delete_document_vectors(document_id)
        except Exception as qdrant_err:
            logger.warning("Failed to clean up Qdrant vectors during error handling: %s", qdrant_err)

        # Transition document status to 'failed' and record audit log in a fresh transaction
        try:
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc_to_fail = res.scalar_one_or_none()
            if doc_to_fail:
                doc_to_fail.status = "failed"
                failure_audit = AuditLog(
                    user_id=doc_to_fail.uploaded_by,
                    action="DOCUMENT_PROCESS_FAILED",
                    entity="documents",
                    entity_id=str(document_id),
                    details={
                        "title": doc_to_fail.title,
                        "error": str(exc),
                        "status": "failed",
                    },
                )
                db.add(failure_audit)
                await db.commit()
        except Exception as status_err:
            logger.error("Failed to update document status to 'failed': %s", status_err)
            await db.rollback()

        return ProcessingResult(
            document_id=document_id,
            status="failed",
            pages_count=0,
            chunks_count=0,
            error=str(exc),
        )
