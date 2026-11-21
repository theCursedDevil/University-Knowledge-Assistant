"""Centralized error handling and custom application exceptions."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error payload definition."""

    code: str = Field(..., description="Machine-readable error identifier.")
    message: str = Field(..., description="Human-readable explanation of the error.")
    details: Optional[Any] = Field(
        default=None, description="Optional granular diagnostics or field errors."
    )


class ErrorResponse(BaseModel):
    """Envelope model for API error responses."""

    error: ErrorDetail


class AppException(Exception):
    """Base exception class for all domain-level application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppException):
    """Raised when an entity or resource does not exist."""

    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class ConflictError(AppException):
    """Raised when a state conflict occurs (e.g. optimistic locking violation)."""

    def __init__(
        self,
        message: str = "Resource conflict detected",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class ValidationError(AppException):
    """Raised when request payload fails semantic validation rules."""

    def __init__(
        self,
        message: str = "Request validation failed",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class UnauthorizedError(AppException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class ForbiddenError(AppException):
    """Raised when the authenticated user lacks permission for the action."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class ExternalServiceError(AppException):
    """Raised when an external dependency (PostgreSQL, Qdrant, MinIO, Redis, Groq) fails."""

    def __init__(
        self,
        service: str,
        message: str = "External service unavailable",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=f"{service} service error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details,
        )
