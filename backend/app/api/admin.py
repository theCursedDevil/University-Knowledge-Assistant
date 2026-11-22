"""Admin analytics and user management API router (C-ADMINSVC, FR-ADMIN-001 through FR-ADMIN-003).

Endpoints:
- GET /admin/stats: Real-time system analytics, counts, category distribution, and audit log.
- GET /admin/users: Lists registered users in PostgreSQL.
- PATCH /admin/users/{id}/role: Updates a user's role assignment (with self-demotion lockout guard).
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.auth_dev import require_admin
from backend.app.core.errors import NotFoundError, ForbiddenError
from backend.app.core.logging import logger
from backend.app.core.cache import cache_client
from backend.app.db.session import get_db, get_read_db, replica_router
from backend.app.db.models import User, Document, DocumentChunkMeta, Conversation, Message, AuditLog

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["Admin"])


class AuditLogResponse(BaseModel):
    """Schema for audit log trail entries."""

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity: str
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminStatsResponse(BaseModel):
    """Schema for comprehensive system analytics."""

    total_documents: int = Field(..., description="Total uploaded documents.")
    processed_documents: int = Field(default=0, description="Successfully processed documents ('ready').")
    failed_documents: int = Field(default=0, description="Documents where ingestion failed.")
    processing_documents: int = Field(default=0, description="Documents currently undergoing processing.")
    total_chunks: int = Field(..., description="Total vector chunks indexed.")
    total_conversations: int = Field(..., description="Total conversation threads.")
    total_messages: int = Field(..., description="Total messages exchanged.")
    total_questions: int = Field(default=0, description="Total user questions asked.")
    total_answers: int = Field(default=0, description="Total assistant answers generated.")
    total_users: int = Field(..., description="Total registered users.")
    documents_by_category: Dict[str, int] = Field(default_factory=dict, description="Count of documents per category.")
    documents_by_status: Dict[str, int] = Field(default_factory=dict, description="Count of documents per processing status.")
    recent_audit_logs: List[AuditLogResponse] = Field(default_factory=list, description="Recent audit log events.")


class UserAdminResponse(BaseModel):
    """Schema for administrator view of a user account."""

    id: uuid.UUID
    name: str
    email: str
    role: str
    oauth_sub: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRoleRequest(BaseModel):
    """Request schema for updating a user's role."""

    role: str = Field(..., description="Target role: student, faculty, or admin.")


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Analytics & KPIs",
    description="Returns aggregate counts, category distribution, and recent audit trail events. Administrator role required.",
)
async def get_admin_stats(
    response: Response,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_read_db),
) -> AdminStatsResponse:
    """Aggregates system statistics from PostgreSQL tables with Redis caching."""
    cache_key = cache_client.build_admin_stats_key()
    cached = cache_client.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        logger.debug("[CACHE] Hit for admin stats '%s'", cache_key)
        return AdminStatsResponse.model_validate(cached)

    response.headers["X-Cache"] = "MISS"
    # 1. Document Lifecycle Counts
    total_docs = await db.scalar(select(func.count(Document.id))) or 0
    processed_docs = await db.scalar(select(func.count(Document.id)).where(Document.status == "ready")) or 0
    failed_docs = await db.scalar(select(func.count(Document.id)).where(Document.status == "failed")) or 0
    processing_docs = await db.scalar(select(func.count(Document.id)).where(Document.status == "processing")) or 0

    # Status breakdown
    status_stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
    status_res = await db.execute(status_stmt)
    docs_by_status = {st or "unknown": cnt for st, cnt in status_res.all()}

    # 2. Chunk, Conversation, Message & User Counts
    total_chunks = await db.scalar(select(func.count(DocumentChunkMeta.id))) or 0
    total_convs = await db.scalar(select(func.count(Conversation.id))) or 0
    total_msgs = await db.scalar(select(func.count(Message.id))) or 0
    total_questions = await db.scalar(select(func.count(Message.id)).where(Message.role == "user")) or 0
    total_answers = await db.scalar(select(func.count(Message.id)).where(Message.role == "assistant")) or 0
    total_users = await db.scalar(select(func.count(User.id))) or 0

    # 3. Documents by Category
    cat_stmt = select(Document.category, func.count(Document.id)).group_by(Document.category)
    cat_result = await db.execute(cat_stmt)
    docs_by_cat = {cat: count for cat, count in cat_result.all()}

    # 4. Recent Audit Logs
    audit_stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)
    audit_res = await db.execute(audit_stmt)
    audit_logs = list(audit_res.scalars().all())

    stats_resp = AdminStatsResponse(
        total_documents=total_docs,
        processed_documents=processed_docs,
        failed_documents=failed_docs,
        processing_documents=processing_docs,
        total_chunks=total_chunks,
        total_conversations=total_convs,
        total_messages=total_msgs,
        total_questions=total_questions,
        total_answers=total_answers,
        total_users=total_users,
        documents_by_category=docs_by_cat,
        documents_by_status=docs_by_status,
        recent_audit_logs=audit_logs,
    )
    cache_client.set(
        cache_key,
        stats_resp.model_dump(mode="json"),
        ttl=settings.CACHE_ADMIN_STATS_TTL,
    )
    return stats_resp


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Query System Audit Logs",
    description="Returns paginated audit trail events with optional filtering by action or entity. Administrator role required.",
)
async def list_audit_logs(
    action: Optional[str] = None,
    entity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_read_db),
) -> List[AuditLogResponse]:
    """Retrieves paginated audit log events for compliance and security auditing."""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action.upper())
    if entity:
        stmt = stmt.where(AuditLog.entity == entity.lower())
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(min(limit, 100))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get(
    "/users",
    response_model=List[UserAdminResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered Users",
    description="Retrieves all registered users from PostgreSQL. Administrator role required.",
)
async def list_admin_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_read_db),
) -> List[UserAdminResponse]:
    """Returns all users ordered by creation date."""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch(
    "/users/{id}/role",
    response_model=UserAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Role",
    description="Updates role of a user. Prevents self-demotion of the logged in administrator.",
)
async def update_user_role(
    id: uuid.UUID,
    payload: UpdateUserRoleRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    """Modifies a user's role while enforcing safety lockout policy."""
    target_role = payload.role.lower()
    if target_role not in ("student", "faculty", "admin"):
        target_role = "student"

    if current_user.id == id and current_user.role == "admin" and target_role != "admin":
        raise ForbiddenError("Safety policy: You cannot remove your own administrative privileges.")

    stmt = select(User).where(User.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User with ID '{id}' not found.", details={"user_id": str(id)})

    old_role = user.role
    user.role = target_role

    audit = AuditLog(
        user_id=current_user.id,
        action="USER_ROLE_UPDATE",
        entity="users",
        entity_id=str(user.id),
        details={"old_role": old_role, "new_role": target_role},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    replica_router.record_user_write(current_user.id)
    cache_client.invalidate_admin_stats()

    logger.info("Updated role for user %s (%s -> %s)", user.id, old_role, target_role)
    return UserAdminResponse.model_validate(user)
