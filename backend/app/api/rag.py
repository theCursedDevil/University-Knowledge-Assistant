"""RAG Question Answering API router (C-RAGSVC).

Endpoints:
- POST /rag/query: Receives natural language question, executes retrieval and grounded LLM generation.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth_dev import get_current_user
from backend.app.db.session import get_db
from backend.app.db.models import User
from backend.app.rag.rag_service import rag_service, RAGResponse

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGQueryRequest(BaseModel):
    """Schema for natural-language RAG queries."""

    question: str = Field(..., min_length=2, max_length=1000, description="User's natural language question.")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Optional recent conversation turns [{'role': 'user'|'assistant', 'content': '...'}]"
    )
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of relevant chunks to retrieve.")
    confidence_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Minimum cosine similarity threshold."
    )
    category: Optional[str] = Field(default=None, description="Optional category filter.")


@router.post(
    "/query",
    response_model=RAGResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask University Knowledge Question",
    description="Answers a university inquiry using top-k semantic vector retrieval, grounded prompt construction, and Groq LLM completion.",
)
async def query_rag(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RAGResponse:
    """Executes the end-to-end RAG pipeline for the authenticated user."""
    return await rag_service.answer_question(
        question=request.question,
        conversation_history=request.conversation_history,
        top_k=request.top_k,
        confidence_threshold=request.confidence_threshold,
        filter_category=request.category,
        session=db,
        user_role=current_user.role,
    )
