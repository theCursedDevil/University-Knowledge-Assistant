"""Health check endpoint providing runtime status and service diagnostics."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, status, Depends
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.core.auth_dev import require_admin
from backend.app.db.models import User

settings = get_settings()
router = APIRouter()


class ServiceStatus(BaseModel):
    """Status description for individual dependencies."""

    configured: bool = Field(..., description="Whether required credentials/endpoints are set.")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Metadata about the service.")


class HealthResponse(BaseModel):
    """Pydantic model validating healthcheck responses."""

    status: str = Field(default="healthy", description="Overall backend health status.")
    app_name: str = Field(..., description="Application name.")
    version: str = Field(..., description="Application version.")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of status check.")


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Backend Health Check",
    description="Returns minimal liveness information without exposing service topology.",
    tags=["Health"],
)
async def get_health() -> HealthResponse:
    """Returns minimal liveness information without exposing service topology."""
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/health/db",
    status_code=status.HTTP_200_OK,
    summary="Database Replication Health Check",
    description="Returns detailed connectivity, standby recovery state, and WAL streaming status for Primary and Replicas.",
    tags=["Health"],
)
async def get_db_health(
    current_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Returns connectivity, standby recovery, and WAL replication metrics across all database nodes."""
    from backend.app.db.session import check_db_connection
    return await check_db_connection()
