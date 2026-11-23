"""Document management API router.

Endpoints:
- POST /documents: Multipart PDF upload, MinIO persistence, DB metadata record, audit log (Admin only).
- GET /documents: List documents with metadata and category filtering.
- DELETE /documents/{id}: Cascading deletion from MinIO and PostgreSQL, audit log (Admin only).
"""

import re
import uuid
from datetime import datetime
from typing import List, Optional, Union, Any
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
    Response,
    status,
    Query,
)
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.errors import (
    AppException,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    ConflictError,
)
from backend.app.core.logging import logger
from backend.app.core.cache import cache_client, async_distributed_lock
from backend.app.core.auth_dev import get_current_user, require_admin
from backend.app.db.session import get_db, get_read_db, replica_router
from backend.app.db.models import User, Document, DocumentChunkMeta, AuditLog
from backend.app.services.storage import storage_service
from backend.app.rag.pipeline import process_document, ProcessingResult
from backend.app.rag.vector_store import vector_store, SearchResult
from backend.app.rag.extractor import extract_text_from_pdf, ExtractedPage

settings = get_settings()
router = APIRouter()


class DocumentUpdateRequest(BaseModel):
    """Schema for updating document title, category, and access restriction with optimistic locking."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role_restriction: Optional[str] = Field(default=None, description="Role restriction: 'all', 'student', 'faculty', 'admin', or empty string to clear.")
    expected_version: Optional[int] = Field(
        default=None,
        description="Expected document version for optimistic concurrency control (FR-DBSYNC-004).",
    )


class DocumentPreviewResponse(BaseModel):
    """Schema for document preview containing extracted pages."""

    id: uuid.UUID
    title: str
    category: str
    role_restriction: Optional[str] = None
    status: str
    storage_path: str
    page_count: int
    pages: List[ExtractedPage]


class DocumentResponse(BaseModel):
    """Schema for document representation."""

    id: uuid.UUID
    title: str
    category: str
    role_restriction: Optional[str] = None
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
    role_restriction: Optional[str] = None
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


def check_document_access(document: Union[Document, DocumentResponse, Any], user: User) -> None:
    """Validates that the user's role permits accessing the document (FR-DOC-010)."""
    if user.role == "admin":
        return
    restr = (document.role_restriction or "").lower().strip()
    if not restr or restr in ("all", "public", "student"):
        return
    if restr == "faculty" and user.role == "faculty":
        return
    raise ForbiddenError(
        message=f"Access denied. This document is restricted to {restr} members.",
        details={"document_id": str(document.id), "required_role": restr, "user_role": user.role},
    )


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
    role_restriction: Optional[str] = Form(default=None, description="Optional role restriction: 'all', 'student', 'faculty', 'admin'."),
    auto_process: Optional[bool] = Query(default=None, description="Automatically trigger processing pipeline in background."),
    auto_process_form: Optional[str] = Form(default=None, alias="auto_process", description="Form field for auto_process."),
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

    # 5. Validate Role Restriction
    sanitized_role_restr = None
    if role_restriction and role_restriction.strip():
        sanitized_role_restr = role_restriction.strip().lower()
        if sanitized_role_restr not in ("all", "student", "faculty", "admin"):
            raise ValidationError(
                message="Invalid role_restriction. Allowed values are 'all', 'student', 'faculty', 'admin'.",
                details={"role_restriction": role_restriction},
            )

    # 6. Generate Unique Identifiers & Storage Path
    doc_id = uuid.uuid4()
    sanitized_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    object_key = f"documents/{doc_id}/{sanitized_filename}"

    # 7. Upload to MinIO Object Storage
    storage_path = storage_service.upload_file(
        object_name=object_key,
        data=content,
        length=file_size,
        content_type="application/pdf",
    )

    # 8. Record Metadata in PostgreSQL with Atomic Rollback Protection
    doc_title = title.strip() if title and title.strip() else filename
    document = Document(
        id=doc_id,
        title=doc_title,
        category=category.strip(),
        role_restriction=sanitized_role_restr,
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
            "role_restriction": sanitized_role_restr,
            "size_bytes": file_size,
            "storage_path": storage_path,
        },
    )

    try:
        db.add(document)
        db.add(audit_entry)
        await db.commit()
        await db.refresh(document)
        # Record write for read-your-own-writes session consistency (FR-DBSYNC-003)
        replica_router.record_user_write(current_user.id, secondary_id=getattr(current_user, "email", None))
        # Invalidate cached document listings and admin stats on upload (FR-CACHE-001)
        cache_client.invalidate_document_caches()
    except Exception as exc:
        logger.error("Database commit failed for doc %s; cleaning up MinIO object: %s", doc_id, exc)
        # Prevent orphaned storage objects
        storage_service.delete_file(storage_path)
        await db.rollback()
        raise

    should_auto_process = True
    if auto_process is not None:
        should_auto_process = auto_process
    elif auto_process_form is not None:
        should_auto_process = str(auto_process_form).strip().lower() in ("true", "1", "yes")

    if should_auto_process:
        background_tasks.add_task(process_document, doc_id)

    logger.info("Document successfully uploaded: id=%s title='%s' category='%s' role_restriction='%s'", doc_id, doc_title, category, sanitized_role_restr)
    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        category=document.category,
        role_restriction=document.role_restriction,
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
    description="Synchronously runs PDF extraction, chunking, embedding generation, and vector indexing for the given document with distributed lock protection. Administrator role required.",
    tags=["Documents"],
)
async def trigger_document_processing(
    id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProcessingResult:
    """Executes the ingestion pipeline for a document with distributed lock protection."""
    stmt = select(Document).where(Document.id == id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )
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
    db: AsyncSession = Depends(get_read_db),
) -> List[DocumentChunkResponse]:
    """Retrieves chunk metadata associated with the document from PostgreSQL."""
    doc_stmt = select(Document).where(Document.id == id)
    doc_res = await db.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )
    check_document_access(doc, current_user)

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
    response: Response,
    category: Optional[str] = Query(default=None, description="Optional category filter."),
    skip: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=100, ge=1, le=500, description="Pagination limit."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> List[DocumentResponse]:
    """Retrieves document records from PostgreSQL with role-based visibility filtering and Redis read-through caching."""
    cache_key = cache_client.build_document_list_key(
        role=current_user.role,
        category=category,
        skip=skip,
        limit=limit,
    )
    cached_docs = cache_client.get(cache_key)
    if cached_docs is not None:
        response.headers["X-Cache"] = "HIT"
        logger.debug("[CACHE] Hit for document list '%s'", cache_key)
        return [DocumentResponse.model_validate(item) for item in cached_docs]

    response.headers["X-Cache"] = "MISS"
    query = select(Document)
    if category:
        query = query.where(Document.category == category)

    # Server-side role visibility filter (FR-DOC-010)
    if current_user.role == "student":
        query = query.where(
            or_(
                Document.role_restriction.is_(None),
                Document.role_restriction.in_(("all", "public", "student")),
            )
        )
    elif current_user.role == "faculty":
        query = query.where(
            or_(
                Document.role_restriction.is_(None),
                Document.role_restriction != "admin",
            )
        )
    # Admin sees all documents

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = list(result.scalars().all())

    # Cache serialized documents list
    serialized = [DocumentResponse.model_validate(d).model_dump(mode="json") for d in docs]
    cache_client.set(cache_key, serialized, ttl=settings.CACHE_DOCUMENTS_LIST_TTL)
    return docs


@router.get(
    "/documents/{id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document by ID",
    description="Retrieves a single document's metadata by its unique identifier.",
    tags=["Documents"],
)
async def get_document(
    id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> DocumentResponse:
    """Retrieves single document metadata with caching and role-based access check."""
    cache_key = cache_client.build_document_detail_key(str(id))
    cached = cache_client.get(cache_key)
    if cached is not None:
        doc_resp = DocumentResponse.model_validate(cached)
        check_document_access(doc_resp, current_user)
        response.headers["X-Cache"] = "HIT"
        return doc_resp

    response.headers["X-Cache"] = "MISS"
    stmt = select(Document).where(Document.id == id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )
    check_document_access(doc, current_user)
    doc_resp = DocumentResponse.model_validate(doc)
    cache_client.set(cache_key, doc_resp.model_dump(mode="json"), ttl=settings.CACHE_DEFAULT_TTL_SECONDS)
    return doc_resp


@router.get(
    "/documents/{id}/preview",
    response_model=DocumentPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview Document Content",
    description="Extracts page-by-page text from the stored MinIO PDF for preview.",
    tags=["Documents"],
)
async def preview_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> DocumentPreviewResponse:
    """Extracts and returns document text pages from MinIO object storage."""
    stmt = select(Document).where(Document.id == id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )
    check_document_access(doc, current_user)

    pages = []
    try:
        pdf_bytes = storage_service.get_file(doc.storage_path)
        pages = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        logger.warning("Could not extract live PDF preview for doc %s: %s", id, exc)

    return DocumentPreviewResponse(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        role_restriction=doc.role_restriction,
        status=doc.status,
        storage_path=doc.storage_path,
        page_count=len(pages),
        pages=pages,
    )


@router.patch(
    "/documents/{id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit Document Metadata",
    description="Updates document title, category, or role restriction with optimistic locking (FR-DBSYNC-004). Administrator role required.",
    tags=["Documents"],
)
async def update_document(
    id: uuid.UUID,
    payload: DocumentUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Updates document metadata using atomic optimistic concurrency control."""
    # 1. Verify existence
    stmt = select(Document).where(Document.id == id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise NotFoundError(
            message=f"Document with ID '{id}' not found.",
            details={"document_id": str(id)},
        )

    # 2. Check for optimistic locking conflict against existing document state
    if payload.expected_version is not None and doc.version != payload.expected_version:
        raise ConflictError(
            message=(
                f"Optimistic lock conflict on document '{id}'. "
                f"Expected version {payload.expected_version}, but current version is {doc.version}. "
                "The document was modified by another transaction. Please refresh the document before updating."
            ),
            details={
                "document_id": str(id),
                "expected_version": payload.expected_version,
                "current_version": doc.version,
                "action_required": "refresh_document",
            },
        )

    # 3. Validate role_restriction if provided
    restr_val = None
    if payload.role_restriction is not None:
        restr_val = payload.role_restriction.strip().lower() if payload.role_restriction.strip() else None
        if restr_val and restr_val not in ("all", "student", "faculty", "admin"):
            raise ValidationError(
                message="Invalid role_restriction. Allowed values are 'all', 'student', 'faculty', 'admin'.",
                details={"role_restriction": payload.role_restriction},
            )

    # 4. Prepare values to update and audit trail
    changes: dict = {}
    values_to_update: dict = {
        "version": Document.version + 1,
        "updated_at": func.now(),
    }

    if payload.title and payload.title.strip():
        changes["old_title"] = doc.title
        changes["new_title"] = payload.title.strip()
        values_to_update["title"] = payload.title.strip()

    if payload.category and payload.category.strip():
        changes["old_category"] = doc.category
        changes["new_category"] = payload.category.strip()
        values_to_update["category"] = payload.category.strip()

    if payload.role_restriction is not None:
        changes["old_role_restriction"] = doc.role_restriction
        changes["new_role_restriction"] = restr_val
        values_to_update["role_restriction"] = restr_val

    # 5. Atomic SQL UPDATE with WHERE id = :id AND version = :expected_version
    where_clauses = [Document.id == id]
    if payload.expected_version is not None:
        where_clauses.append(Document.version == payload.expected_version)

    update_stmt = (
        update(Document)
        .where(*where_clauses)
        .values(**values_to_update)
    )
    result = await db.execute(update_stmt)

    if result.rowcount == 0:
        # Atomic update matched zero rows indicating concurrent modification
        refreshed = (await db.execute(select(Document).where(Document.id == id))).scalar_one_or_none()
        current_ver = refreshed.version if refreshed else None
        raise ConflictError(
            message=(
                f"Optimistic lock conflict on document '{id}'. "
                f"Expected version {payload.expected_version}, but current version is {current_ver}. "
                "The document was modified by another transaction. Please refresh the document before updating."
            ),
            details={
                "document_id": str(id),
                "expected_version": payload.expected_version,
                "current_version": current_ver,
                "action_required": "refresh_document",
            },
        )

    # 6. Record audit log
    changes["expected_version"] = payload.expected_version
    changes["new_version"] = doc.version + 1
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_METADATA_UPDATE",
        entity="documents",
        entity_id=str(doc.id),
        details=changes,
    )
    db.add(audit)
    await db.commit()

    # 7. Record write for read-your-own-writes session consistency (FR-DBSYNC-003)
    replica_router.record_user_write(current_user.id, secondary_id=getattr(current_user, "email", None))
    cache_client.invalidate_document_caches(document_id=str(id))

    # 8. Reload refreshed document
    refreshed_doc = (await db.execute(select(Document).where(Document.id == id))).scalar_one()
    return DocumentResponse.model_validate(refreshed_doc)


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
    """Executes cascading deletion across MinIO, Qdrant, and PostgreSQL with distributed lock protection."""
    async with async_distributed_lock(f"document:{id}", expire_seconds=30.0, timeout_seconds=1.0):
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
        replica_router.record_user_write(current_user.id, secondary_id=getattr(current_user, "email", None))
        cache_client.invalidate_document_caches(document_id=str(id))

        logger.info("Document deleted: id=%s title='%s'", id, document.title)
        return DocumentDeleteResponse(
            message="Document successfully deleted",
            id=id,
        )


class DocumentSearchRequest(BaseModel):
    """Schema for semantic vector search requests."""

    query: str = Field(..., min_length=2, max_length=1000, description="Semantic text query.")
    limit: int = Field(default=5, ge=1, le=50, description="Number of top results to return.")
    score_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity.")
    category: Optional[str] = Field(default=None, description="Filter by document category.")
    document_id: Optional[uuid.UUID] = Field(default=None, description="Filter by specific document ID.")


@router.post(
    "/documents/search",
    response_model=List[SearchResult],
    status_code=status.HTTP_200_OK,
    summary="Semantic Vector Search",
    description="Performs top-k cosine similarity search against indexed document chunks using all-MiniLM-L6-v2 embeddings.",
    tags=["Documents"],
)
async def search_documents(
    search_request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
) -> List[SearchResult]:
    """Retrieves top-k relevant chunks from Qdrant matching the search query, filtered by user role permissions."""
    return vector_store.search(
        query=search_request.query,
        limit=search_request.limit,
        score_threshold=search_request.score_threshold,
        filter_category=search_request.category,
        filter_document_id=search_request.document_id,
        user_role=current_user.role,
    )
