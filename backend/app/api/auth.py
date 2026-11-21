"""Authentication and user identity API router (C-AUTHSVC, FR-AUTH-001 through FR-AUTH-004).

Endpoints:
- GET /me: Current user profile and role assignments.
- POST /auth/login: Development login entry point.
- GET /auth/callback: OAuth 2.0 / OIDC redirect handler.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth_dev import get_current_user, get_or_create_dev_user
from backend.app.core.logging import logger
from backend.app.db.session import get_db
from backend.app.db.models import User

router = APIRouter(tags=["Auth"])


class UserResponse(BaseModel):
    """Schema for user profile representation."""

    id: uuid.UUID
    oauth_sub: str
    name: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Request schema for login entry point."""

    email: str = Field(..., description="User email address.")
    role: Optional[str] = Field(default="student", description="Role persona: student, faculty, or admin.")
    name: Optional[str] = None


class LoginResponse(BaseModel):
    """Response schema returned after successful login."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role assignments of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns the authenticated user's record from PostgreSQL."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login Entry Point",
    description="Authenticates or provisions a development user in PostgreSQL and returns an access token.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Provisions or fetches the specified user and issues a bearer token."""
    role = payload.role or "student"
    if role not in ("student", "faculty", "admin"):
        role = "student"

    user = await get_or_create_dev_user(
        db=db,
        role=role,
        email=payload.email,
        name=payload.name,
    )

    logger.info("User logged in: id=%s email=%s role=%s", user.id, user.email, user.role)
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=f"dev-token-{user.role}-{user.id}",
        token_type="bearer",
    )


@router.get(
    "/auth/callback",
    status_code=status.HTTP_200_OK,
    summary="OAuth 2.0 Redirect Handler",
    description="Handles OAuth 2.0 authorization code callbacks from Keycloak.",
)
async def oauth_callback(
    code: Optional[str] = Query(default=None, description="Authorization code from Keycloak"),
    state: Optional[str] = Query(default=None, description="CSRF state token"),
):
    """Stub redirect handler for Keycloak OAuth 2.0 callback."""
    return {
        "status": "success",
        "message": "OAuth callback processed successfully",
        "code_received": bool(code),
        "state": state,
    }
