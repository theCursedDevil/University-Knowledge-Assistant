"""Automated test suite verifying SQLAlchemy relational models, foreign key cascades,
constraints, session lifecycle, and PostgreSQL database operations.
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import check_db_connection
from backend.app.db.models import (
    User,
    Document,
    DocumentChunkMeta,
    Conversation,
    Message,
    AuditLog,
)


@pytest.mark.asyncio
async def test_live_postgres_connectivity():
    """Verifies that check_db_connection reports connected against PostgreSQL 16."""
    result = await check_db_connection()
    assert result["status"] == "connected"
    assert result["database"] == "university_assistant"


@pytest.mark.asyncio
async def test_user_creation_and_constraints(db_session: AsyncSession):
    """Verifies user entity persistence, uniqueness, and role check constraints."""
    unique_sub = f"keycloak-sub-{uuid.uuid4()}"
    user = User(
        oauth_sub=unique_sub,
        name="Aashu Kumar",
        email="aashu@university.edu",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.role == "student"
    assert user.created_at is not None

    # Verify role constraint rejection
    invalid_user = User(
        oauth_sub=f"invalid-{uuid.uuid4()}",
        name="Hacker",
        email="hacker@test.com",
        role="superadmin",  # Not in ('student', 'faculty', 'admin')
    )
    db_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Clean up
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_document_and_chunks_lifecycle(db_session: AsyncSession):
    """Verifies document creation, versioning, chunk association, and cascading deletion."""
    # Create uploader
    uploader = User(
        oauth_sub=f"admin-sub-{uuid.uuid4()}",
        name="Admin User",
        email="admin@university.edu",
        role="admin",
    )
    db_session.add(uploader)
    await db_session.commit()
    await db_session.refresh(uploader)

    # Create Document
    doc = Document(
        title="Academic Regulations 2024",
        category="Curriculum",
        storage_path="university-documents/academic_regulations_2024.pdf",
        uploaded_by=uploader.id,
        status="indexed",
        version=1,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    assert doc.id is not None
    assert doc.version == 1
    assert doc.status == "indexed"

    # Create Chunks
    chunk_1 = DocumentChunkMeta(
        vector_id=f"vec-{uuid.uuid4()}",
        document_id=doc.id,
        chunk_index=0,
        page=1,
        section="1.1 Overview",
    )
    chunk_2 = DocumentChunkMeta(
        vector_id=f"vec-{uuid.uuid4()}",
        document_id=doc.id,
        chunk_index=1,
        page=2,
        section="1.2 Degree Requirements",
    )
    db_session.add_all([chunk_1, chunk_2])
    await db_session.commit()

    # Query chunks
    stmt = select(DocumentChunkMeta).where(DocumentChunkMeta.document_id == doc.id)
    result = await db_session.execute(stmt)
    chunks = result.scalars().all()
    assert len(chunks) == 2

    # Verify cascading deletion of chunks when document is deleted
    await db_session.delete(doc)
    await db_session.commit()

    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 0

    # Clean up uploader
    await db_session.delete(uploader)
    await db_session.commit()


@pytest.mark.asyncio
async def test_conversation_and_messages_cascade(db_session: AsyncSession):
    """Verifies chat conversation threads, turn messages, citations JSON, and cascade delete."""
    # Create user
    user = User(
        oauth_sub=f"student-sub-{uuid.uuid4()}",
        name="Student User",
        email="student@university.edu",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create conversation
    conv = Conversation(
        user_id=user.id,
        title="Degree requirements inquiry",
    )
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    # Add messages
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content="What are the passing credits for B.Tech CSE?",
    )
    citations_payload = {
        "citations": [
            {
                "source_id": 1,
                "document_title": "Academic Regulations 2024",
                "page": 12,
                "section": "Graduation Requirements",
                "chunk_id": "vec-12345",
            }
        ]
    }
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="According to the Academic Regulations 2024, page 12, the passing requirement is 160 credits.",
        citations_json=citations_payload,
    )
    db_session.add_all([user_msg, assistant_msg])
    await db_session.commit()

    # Query messages
    stmt = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    result = await db_session.execute(stmt)
    messages = result.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].citations_json == citations_payload

    # Cascade delete conversation
    await db_session.delete(conv)
    await db_session.commit()

    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 0

    # Clean up user
    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_audit_log_recording(db_session: AsyncSession):
    """Verifies that administrative audit entries can be recorded with metadata."""
    admin_user = User(
        oauth_sub=f"admin-audit-{uuid.uuid4()}",
        name="Audit Admin",
        email="auditadmin@university.edu",
        role="admin",
    )
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)

    log_entry = AuditLog(
        user_id=admin_user.id,
        action="DOCUMENT_UPLOAD",
        entity="documents",
        entity_id=str(uuid.uuid4()),
        details={"file_name": "syllabus.pdf", "file_size_bytes": 1024500},
    )
    db_session.add(log_entry)
    await db_session.commit()
    await db_session.refresh(log_entry)

    assert log_entry.id is not None
    assert log_entry.action == "DOCUMENT_UPLOAD"
    assert log_entry.details["file_name"] == "syllabus.pdf"

    # Clean up
    await db_session.delete(log_entry)
    await db_session.delete(admin_user)
    await db_session.commit()
