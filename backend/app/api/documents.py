"""Document management API router.

Endpoints:
- POST /documents: Multipart PDF upload, MinIO persistence, DB metadata record, audit log (Admin only).
- GET /documents: List documents with metadata and category filtering.
- DELETE /documents/{id}: Cascading deletion from MinIO and PostgreSQL, audit log (Admin only).
"""

import re
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
    status,
    Query,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.errors import (
    AppException,
    NotFoundError,
    ValidationError,
)
from backend.app.core.logging import logger
from backend.app.core.auth_dev import get_current_user, require_admin
from backend.app.db.session import get_db
from backend.app.db.models import User, Document, DocumentChunkMeta, AuditLog
from backend.app.services.storage import storage_service
from backend.app.rag.pipeline import process_document, ProcessingResult
from backend.app.rag.vector_store import vector_store

settings = get_settings()
router = APIRouter()


class DocumentResponse(BaseModel):
    """Schema for document representation."""

    id: uuid.UUID
    title: str
    category: str
    storage_path: str
    uploaded_by: Optional[uuid.UUID] = None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Schema returned after a successful document upload."""

    id: uuid.UUID
    title: str
    category: str
    storage_path: str
    status: str
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDeleteResponse(BaseModel):
    """Schema returned after document deletion."""

    message: str = Field(default="Document successfully deleted")
    id: uuid.UUID


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk metadata linking source page and vector point."""

    id: uuid.UUID
    vector_id: str
    chunk_index: int
    page: Optional[int] = None
    section: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF Document",
    description="Validates and uploads a university knowledge PDF to MinIO and registers metadata in PostgreSQL. Administrator role required.",
    tags=["Documents"],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document file to upload."),
    category: str = Form(..., description="Document category (e.g. 'Academic', 'Admissions', 'Hostel', 'Regulations')."),
    title: Optional[str] = Form(default=None, description="Optional custom document title."),
    auto_process: bool = Query(default=True, description="Automatically trigger processing pipeline in background."),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Handles multipart PDF upload with MIME/extension checks, MinIO storage, and audit logging."""
    # 1. Validate File Extension
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise ValidationError(
            message="Invalid file format. Only PDF (.pdf) documents are accepted.",
            details={"filename": filename, "allowed_extensions": [".pdf"]},
        )

    # 2. Validate MIME Type
    content_type = file.content_type or ""
    if content_type.lower() not in ("application/pdf", "application/x-pdf"):
        raise ValidationError(
            message="Invalid MIME type. Must be 'application/pdf'.",
            details={"content_type": content_type},
        )

    # 3. Read File Content & Check Size
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise ValidationError(message="Uploaded file is empty (0 bytes).")

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise AppException(
            message=f"File size ({file_size} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes (25MB).",
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"size_bytes": file_size, "max_bytes": settings.MAX_UPLOAD_SIZE_BYTES},
        )

    # 4. Validate Magic Bytes (%PDF-)
    if not content.startswith(b"%PDF"):
        raise ValidationError(
            message="Invalid PDF content. File header does not match valid PDF magic bytes.",
            details={"header": content[:8].decode("latin-1", errors="replace")},
        )

    # 5. Generate Unique Identifiers & Storage Path
    doc_id = uuid.uuid4()
    sanitized_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    object_key = f"documents/{doc_id}/{sanitized_filename}"

    # 6. Upload to MinIO Object Storage
    storage_path = storage_service.upload_file(
        object_name=object_key,
        data=content,
        length=file_size,
        content_type="application/pdf",
    )

    # 7. Record Metadata in PostgreSQL with Atomic Rollback Protection
    doc_title = title.strip() if title and title.strip() else filename
    document = Document(
        id=doc_id,
        title=doc_title,
        category=category.strip(),
        storage_path=storage_path,
        uploaded_by=current_user.id,
        status="processing",
        version=1,
    )

    audit_entry = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_UPLOAD",
        entity="documents",
        entity_id=str(doc_id),
        details={
            "filename": filename,
            "category": category,
            "size_bytes": file_size,
            "storage_path": storage_path,
        },
    )

    try:
        db.add(document)
        db.add(audit_entry)
        await db.commit()
        await db.refresh(document)
    except Exception as exc:
        logger.error("Database commit failed for doc %s; cleaning up MinIO object: %s", doc_id, exc)
        # Prevent orphaned storage objects
        storage_service.delete_file(storage_path)
        await db.rollback()
        raise

    if auto_process:
        background_tasks.add_task(process_document, doc_id)

    logger.info("Document successfully uploaded: id=%s title='%s' category='%s'", doc_id, doc_title, category)
    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        category=document.category,
        storage_path=document.storage_path,
        status=document.status,
        version=document.version,
        created_at=document.created_at,
    )


@router.post(
    "/documents/{id}/process",
    response_model=ProcessingResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger Document Ingestion Pipeline",
    description="Synchronously runs PDF extraction, chunking, embedding generation, and vector indexing for the given document. Administrator role required.",
    tags=["Documents"],
)
async def trigger_document_processing(
    id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProcessingResult:
    """Executes the ingestion pipeline for a document."""
    return await process_document(id, session=db)


@router.get(
    "/documents/{id}/chunks",
    response_model=List[DocumentChunkResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Document Chunks Metadata",
    description="Lists all indexed chunks and page provenance for a given document.",
    tags=["Documents"],
)
async def get_document_chunks(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentChunkResponse]:
    """Retrieves chunk metadata associated with the document from PostgreSQL."""
    doc_stmt = select(Document).where(Document.id == id)
    doc_res = await db.execute(doc_stmt)
    if not doc_res.scalar_one_or_none():
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )

    stmt = (
        select(DocumentChunkMeta)
        .where(DocumentChunkMeta.document_id == id)
        .order_by(DocumentChunkMeta.chunk_index.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/documents",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Documents",
    description="Returns all uploaded university documents with optional category filtering and pagination.",
    tags=["Documents"],
)
async def list_documents(
    category: Optional[str] = Query(default=None, description="Optional category filter."),
    skip: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=100, ge=1, le=500, description="Pagination limit."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Retrieves document records from PostgreSQL."""
    query = select(Document)
    if category:
        query = query.where(Document.category == category)

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()
    return list(docs)


@router.delete(
    "/documents/{id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Deletes a document from MinIO object storage and PostgreSQL, cascading to chunk metadata and vector points. Administrator role required.",
    tags=["Documents"],
)
async def delete_document(
    id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentDeleteResponse:
    """Executes cascading deletion across MinIO, Qdrant, and PostgreSQL with audit trail logging."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )

    # 1. Remove object from MinIO
    storage_path = document.storage_path
    if storage_service.file_exists(storage_path):
        storage_service.delete_file(storage_path)

    # 2. Remove vector points from Qdrant
    try:
        vector_store.delete_document_vectors(id)
    except Exception as exc:
        logger.warning("Failed to delete Qdrant vectors for doc %s: %s", id, exc)

    # 3. Record audit log entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_DELETE",
        entity="documents",
        entity_id=str(id),
        details={"title": document.title, "storage_path": storage_path},
    )
    db.add(audit_entry)

    # 4. Delete from database (cascades to document_chunks_meta)
    await db.delete(document)
    await db.commit()

    logger.info("Document deleted: id=%s title='%s'", id, document.title)
    return DocumentDeleteResponse(
        message="Document successfully deleted",
        id=id,
    )
