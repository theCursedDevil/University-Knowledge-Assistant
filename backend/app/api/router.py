"""Central API router aggregating all versioned endpoints."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router

api_router = APIRouter()

# Mount health routes under API prefix (e.g. /api/v1/health)
api_router.include_router(health_router, tags=["Health"])

# Future Phase Routers will be registered here:
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
# api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
# api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
# api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
