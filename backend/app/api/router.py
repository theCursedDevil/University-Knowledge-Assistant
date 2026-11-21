"""Central API router aggregating all versioned endpoints."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.documents import router as documents_router
from backend.app.api.rag import router as rag_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.auth import router as auth_router
from backend.app.api.admin import router as admin_router

api_router = APIRouter()

# Mount health routes under API prefix (e.g. /api/v1/health)
api_router.include_router(health_router, tags=["Health"])

# Mount document management routes under API prefix (/api/v1/documents)
api_router.include_router(documents_router, tags=["Documents"])

# Mount core RAG query route under API prefix (/api/v1/rag/query)
api_router.include_router(rag_router, tags=["RAG"])

# Mount conversation and message routes under API prefix (/api/v1/conversations)
api_router.include_router(conversations_router, tags=["Conversations"])

# Mount authentication & user identity routes under API prefix (/api/v1/me, /api/v1/auth)
api_router.include_router(auth_router, tags=["Auth"])

# Mount admin analytics & user management routes under API prefix (/api/v1/admin)
api_router.include_router(admin_router, tags=["Admin"])
