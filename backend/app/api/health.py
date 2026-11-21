"""Health check endpoint providing runtime status and service diagnostics."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings
from backend.app.services.external import ExternalServicesConfig

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
    environment: str = Field(..., description="Runtime environment.")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of status check.")
    services: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration summary of external dependencies."
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Backend Health Check",
    description="Returns backend health status, application version, environment, and external service configuration state.",
    tags=["Health"],
)
async def get_health() -> HealthResponse:
    """Returns the backend's health status and service metadata."""
    services_summary = ExternalServicesConfig.get_summary()

    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services_summary,
    )
