"""Comprehensive tests for health check endpoints, Swagger docs, OpenAPI schema,
custom error handling structures, database session module, and external service configuration.
"""

import pytest
from starlette.testclient import TestClient
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.core.config import Settings
from backend.app.core.errors import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    ExternalServiceError,
)
from backend.app.db.session import check_db_connection
from backend.app.services.external import ExternalServicesConfig


def test_root_health_endpoint(client: TestClient, settings: Settings):
    """Verifies that GET /health returns 200 OK and valid health metadata."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.ENVIRONMENT
    assert "timestamp" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert "qdrant" in data["services"]
    assert "minio" in data["services"]
    assert "llm" in data["services"]


def test_api_v1_health_endpoint(client: TestClient, settings: Settings):
    """Verifies that GET /api/v1/health returns 200 OK and matches the health schema."""
    response = client.get(f"{settings.API_V1_PREFIX}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.PROJECT_NAME


def test_swagger_documentation(client: TestClient):
    """Verifies that GET /docs serves the FastAPI Swagger UI HTML page."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower() or "html" in response.headers.get("content-type", "").lower()


def test_redoc_documentation(client: TestClient):
    """Verifies that GET /redoc serves ReDoc documentation."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower() or "html" in response.headers.get("content-type", "").lower()


def test_openapi_schema(client: TestClient, settings: Settings):
    """Verifies that GET /openapi.json produces valid OpenAPI 3.x JSON specification."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == settings.PROJECT_NAME
    assert schema["info"]["version"] == settings.VERSION
    assert "/health" in schema["paths"]
    assert f"{settings.API_V1_PREFIX}/health" in schema["paths"]


def test_not_found_structured_error(client: TestClient):
    """Verifies that non-existent routes return standardized ErrorResponse JSON with 404 status."""
    response = client.get("/non-existent-endpoint-path")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


def test_custom_app_exceptions_handling(app):
    """Verifies that domain AppException instances are properly serialized by exception handlers."""
    test_router = APIRouter(prefix="/test-errors")

    @test_router.get("/conflict")
    def trigger_conflict():
        raise ConflictError("Document version conflict", details={"expected_version": 2})

    @test_router.get("/forbidden")
    def trigger_forbidden():
        raise ForbiddenError("Faculty role required")

    @test_router.get("/unauthorized")
    def trigger_unauthorized():
        raise UnauthorizedError("Missing Bearer token")

    @test_router.get("/validation")
    def trigger_validation():
        raise ValidationError("Invalid query filter", details={"field": "category"})

    @test_router.get("/external")
    def trigger_external():
        raise ExternalServiceError("Qdrant", "Cluster unreachable")

    app.include_router(test_router)

    with TestClient(app) as test_client:
        # Conflict
        r = test_client.get("/test-errors/conflict")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "CONFLICT"
        assert r.json()["error"]["details"]["expected_version"] == 2

        # Forbidden
        r = test_client.get("/test-errors/forbidden")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "FORBIDDEN"

        # Unauthorized
        r = test_client.get("/test-errors/unauthorized")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"

        # Validation
        r = test_client.get("/test-errors/validation")
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

        # External service
        r = test_client.get("/test-errors/external")
        assert r.status_code == 502
        assert r.json()["error"]["code"] == "EXTERNAL_SERVICE_ERROR"


def test_request_validation_error_handler(app):
    """Verifies that Pydantic schema validation failures return formatted ErrorResponse."""
    test_router = APIRouter(prefix="/test-validation")

    class SamplePayload(BaseModel):
        title: str = Field(..., min_length=3)
        count: int = Field(..., ge=1)

    @test_router.post("/items")
    def create_item(payload: SamplePayload):
        return {"status": "ok", "payload": payload.model_dump()}

    app.include_router(test_router)

    with TestClient(app) as test_client:
        # Invalid body (empty json)
        r = test_client.post("/test-validation/items", json={})
        assert r.status_code == 422
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert isinstance(body["error"]["details"], list)


@pytest.mark.asyncio
async def test_database_connection_check_fallback():
    """Verifies that check_db_connection handles disconnected state gracefully without raising."""
    result = await check_db_connection()
    assert "status" in result
    assert result["status"] in ("connected", "disconnected")
    assert "database" in result


def test_external_services_config_summary():
    """Verifies that ExternalServicesConfig returns properly structured service configuration."""
    summary = ExternalServicesConfig.get_summary()
    assert "database" in summary
    assert "redis" in summary
    assert "qdrant" in summary
    assert "minio" in summary
    assert "keycloak" in summary
    assert "llm" in summary
    assert summary["llm"]["provider"] == "Groq"
    assert summary["llm"]["model"] == "llama-3.1-8b-instant"
