"""Conversation and message management API router (C-CHATSVC, FR-CHAT-001 through FR-CHAT-005).

Endpoints:
- POST /conversations: Create a new conversation thread.
- GET /conversations: List all conversation threads owned by the current user.
- GET /conversations/{id}: Retrieve a specific conversation thread and its messages (owner-only).
- POST /conversations/{id}/messages: Submit a user question, retrieve recent turns, invoke RAG, and record turn.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth_dev import get_current_user
from backend.app.core.errors import NotFoundError, ForbiddenError
from backend.app.core.logging import logger
from backend.app.db.session import get_db
from backend.app.db.models import User, Conversation, Message
from backend.app.rag.rag_service import rag_service
from backend.app.rag.citation import Citation

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """Schema for a single chat message turn."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations_json: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Schema for conversation summary representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Schema for a conversation thread with all its associated messages."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Request schema for creating a new conversation."""

    title: Optional[str] = Field(default="New Conversation", max_length=255)


class MessageCreate(BaseModel):
    """Request schema for posting a new user message in a conversation."""

    content: str = Field(..., min_length=1, max_length=4000, description="User question or follow-up prompt.")


class ChatTurnResponse(BaseModel):
    """Response returned upon posting a message and generating the assistant answer."""

    conversation_id: uuid.UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    citations: List[Citation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conversation",
    description="Creates a new persistent conversation thread for the authenticated user.",
)
async def create_conversation(
    payload: Optional[ConversationCreate] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Provisions a new conversation in PostgreSQL."""
    title = (payload.title if payload and payload.title else "New Conversation").strip()
    conversation = Conversation(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    logger.info("Created conversation %s for user %s ('%s')", conversation.id, current_user.id, conversation.title)
    return conversation


@router.get(
    "",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Conversations",
    description="Returns all conversation threads owned by the current user, ordered by most recently updated.",
)
async def list_conversations(
    skip: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=50, ge=1, le=100, description="Pagination limit."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Retrieves current user's conversations from PostgreSQL."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return list(conversations)


@router.get(
    "/{id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conversation Messages",
    description="Retrieves a conversation and all its messages. Restricted strictly to the conversation owner.",
)
async def get_conversation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Fetches conversation thread and verifies ownership."""
    stmt = select(Conversation).where(Conversation.id == id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise NotFoundError(
            message=f"Conversation with ID '{id}' not found.",
            details={"conversation_id": str(id)},
        )

    # Requirement 7: Restrict conversation access to the owning user
    if conversation.user_id != current_user.id:
        logger.warning(
            "Access denied: User %s attempted to view conversation %s owned by %s",
            current_user.id,
            id,
            conversation.user_id,
        )
        raise ForbiddenError(
            message="Access denied. You do not own this conversation.",
            details={"conversation_id": str(id)},
        )

    # Fetch messages ordered chronologically (user before assistant on same timestamp)
    role_order_asc = case((Message.role == "user", 1), (Message.role == "assistant", 2), else_=3)
    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == id)
        .order_by(Message.created_at.asc(), role_order_asc.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = list(msg_res.scalars().all())

    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.post(
    "/{id}/messages",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Question in Conversation",
    description="Saves user question, loads recent turns for context, runs grounded RAG, and saves assistant answer with citations.",
)
async def post_message(
    id: uuid.UUID,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatTurnResponse:
    """Executes a multi-turn conversational exchange with RAG context."""
    # 1. Fetch and verify conversation ownership
    stmt = select(Conversation).where(Conversation.id == id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise NotFoundError(
            message=f"Conversation with ID '{id}' not found.",
            details={"conversation_id": str(id)},
        )

    if conversation.user_id != current_user.id:
        logger.warning(
            "Access denied: User %s attempted to post to conversation %s owned by %s",
            current_user.id,
            id,
            conversation.user_id,
        )
        raise ForbiddenError(
            message="Access denied. You do not own this conversation.",
            details={"conversation_id": str(id)},
        )

    # 2. Save user message
    now = datetime.now(timezone.utc)
    user_content = message_in.content.strip()
    user_message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=user_content,
        created_at=now,
    )
    db.add(user_message)
    await db.flush()

    # 3. Retrieve the last 6 messages (prior to this message) for follow-up conversational context
    # In descending order, assistant should precede user when created_at ties so reversed() maintains user -> assistant
    role_order_desc = case((Message.role == "assistant", 2), (Message.role == "user", 1), else_=0)
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id, Message.id != user_message.id)
        .order_by(Message.created_at.desc(), role_order_desc.desc())
        .limit(6)
    )
    history_res = await db.execute(history_stmt)
    recent_turns = list(reversed(history_res.scalars().all()))
    history_payload = [{"role": m.role, "content": m.content} for m in recent_turns]

    # 4. Invoke RAG pipeline with question, history, and database session
    rag_result = await rag_service.answer_question(
        question=user_content,
        conversation_history=history_payload,
        session=db,
    )

    # 5. Save completed assistant message and citation data
    assistant_now = datetime.now(timezone.utc)
    citations_data = [cit.model_dump() for cit in rag_result.citations] if rag_result.citations else None
    assistant_message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content=rag_result.answer,
        citations_json=citations_data,
        created_at=assistant_now,
    )
    db.add(assistant_message)

    # 6. Update conversation's updated_at timestamp and generate title if default
    conversation.updated_at = datetime.now(timezone.utc)
    if conversation.title == "New Conversation":
        conversation.title = user_content[:50].strip()

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)

    logger.info(
        "Chat turn completed for conv %s: user message %s -> assistant message %s (%d citations)",
        conversation.id,
        user_message.id,
        assistant_message.id,
        len(rag_result.citations),
    )

    return ChatTurnResponse(
        conversation_id=conversation.id,
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(assistant_message),
        citations=rag_result.citations,
    )
