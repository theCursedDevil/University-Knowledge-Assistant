"""Authentication and user identity API router (C-AUTHSVC, FR-AUTH-001 through FR-AUTH-004).

Endpoints:
- GET /me: Current user profile and role assignments.
- POST /auth/login: Development login entry point.
- POST /auth/token: Authorization code and PKCE exchange endpoint (sets httpOnly cookies).
- POST /auth/refresh: Refresh token exchange endpoint (updates httpOnly cookies).
- POST /auth/logout: Revokes session at Keycloak and clears httpOnly cookies.
- GET /auth/config: Returns public Keycloak configuration for the frontend.
- GET /auth/callback: OAuth 2.0 / OIDC redirect handler.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.errors import UnauthorizedError
from backend.app.core.logging import logger
from backend.app.core.security import (
    get_current_user,
    get_or_create_dev_user,
    get_or_provision_user_from_claims,
    token_validator,
    keycloak_service,
)
from backend.app.db.session import get_db
from backend.app.db.models import User

settings = get_settings()
router = APIRouter(tags=["Auth"])


class UserResponse(BaseModel):
    """Schema for user profile representation."""

    id: uuid.UUID
    oauth_sub: str
    name: str
    email: str
    role: str
    roles: List[str] = Field(default_factory=list, description="Active user realm and application roles.")
    created_at: datetime

    model_config = {"from_attributes": True}


def to_user_response(user: User) -> UserResponse:
    """Constructs UserResponse ensuring both primary role and roles list are populated."""
    roles = [user.role]
    if user.role == "admin" and "faculty" not in roles:
        roles.append("faculty")
    return UserResponse(
        id=user.id,
        oauth_sub=user.oauth_sub,
        name=user.name,
        email=user.email,
        role=user.role,
        roles=roles,
        created_at=user.created_at,
    )


class LoginRequest(BaseModel):
    """Request schema for dev login entry point."""

    email: str = Field(..., description="User email address.")
    role: Optional[str] = Field(default="student", description="Role persona: student, faculty, or admin.")
    name: Optional[str] = None


class LoginResponse(BaseModel):
    """Response schema returned after successful login."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class TokenExchangeRequest(BaseModel):
    """Request schema for PKCE authorization code exchange."""

    code: str = Field(..., description="Authorization code returned by Keycloak.")
    code_verifier: str = Field(..., description="Original PKCE code verifier string.")
    redirect_uri: str = Field(..., description="Redirect URI registered with Keycloak client.")


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: Optional[str] = Field(default=None, description="Optional refresh token if not stored in cookie.")


class KeycloakConfigResponse(BaseModel):
    """Public Keycloak connection details for client-side OIDC initialization."""

    keycloak_url: str
    realm: str
    client_id: str


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
    return to_user_response(current_user)


@router.get(
    "/auth/config",
    response_model=KeycloakConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Keycloak Configuration",
    description="Provides frontend with Keycloak server URL, realm, and public client ID.",
)
async def get_keycloak_config() -> KeycloakConfigResponse:
    """Returns public Keycloak OIDC parameters."""
    return KeycloakConfigResponse(
        keycloak_url=settings.KEYCLOAK_URL,
        realm=settings.KEYCLOAK_REALM,
        client_id=settings.KEYCLOAK_CLIENT_ID,
    )


@router.post(
    "/auth/token",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Authorization Code (PKCE)",
    description="Exchanges Keycloak authorization code + PKCE verifier for tokens and sets secure httpOnly cookies.",
)
async def exchange_token(
    payload: TokenExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Exchanges PKCE authorization code with Keycloak, provisions user, and sets cookies."""
    token_data = await keycloak_service.exchange_code_for_tokens(
        code=payload.code,
        code_verifier=payload.code_verifier,
        redirect_uri=payload.redirect_uri,
    )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 1800)
    refresh_expires_in = token_data.get("refresh_expires_in", 3600)

    if not access_token:
        raise UnauthorizedError("Keycloak did not return an access token.")

    claims = token_validator.validate_token(access_token)
    user = await get_or_provision_user_from_claims(db=db, claims=claims)

    # Secure httpOnly cookie storage (never expose tokens to localStorage)
    response.set_cookie(
        key="uka_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=expires_in,
        secure=settings.is_cookie_secure,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key="uka_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            max_age=refresh_expires_in,
            secure=settings.is_cookie_secure,
            path="/",
        )

    logger.info("[AUTH] Completed PKCE token exchange for user=%s role=%s", user.email, user.role)
    return LoginResponse(
        user=to_user_response(user),
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/auth/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Refreshes access token using httpOnly cookie or payload refresh token.",
)
async def refresh_session(
    request: Request,
    response: Response,
    payload: Optional[TokenRefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Exchanges refresh token with Keycloak for renewed tokens."""
    refresh_token = None
    if payload and payload.refresh_token:
        refresh_token = payload.refresh_token
    elif "uka_refresh_token" in request.cookies:
        refresh_token = request.cookies.get("uka_refresh_token")

    if not refresh_token:
        raise UnauthorizedError("No refresh token provided in cookie or payload.")

    token_data = await keycloak_service.refresh_tokens(refresh_token)
    access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token") or refresh_token
    expires_in = token_data.get("expires_in", 1800)
    refresh_expires_in = token_data.get("refresh_expires_in", 3600)

    if not access_token:
        raise UnauthorizedError("Keycloak failed to issue new access token.")

    claims = token_validator.validate_token(access_token)
    user = await get_or_provision_user_from_claims(db=db, claims=claims)

    response.set_cookie(
        key="uka_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=expires_in,
        secure=settings.is_cookie_secure,
        path="/",
    )
    response.set_cookie(
        key="uka_refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="lax",
        max_age=refresh_expires_in,
        secure=settings.is_cookie_secure,
        path="/",
    )

    return LoginResponse(
        user=to_user_response(user),
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Terminates Keycloak SSO session and clears session cookies.",
)
async def logout(
    request: Request,
    response: Response,
    payload: Optional[TokenRefreshRequest] = None,
):
    """Revokes Keycloak session and deletes authentication cookies."""
    refresh_token = None
    if payload and payload.refresh_token:
        refresh_token = payload.refresh_token
    elif "uka_refresh_token" in request.cookies:
        refresh_token = request.cookies.get("uka_refresh_token")

    if refresh_token:
        try:
            await keycloak_service.logout(refresh_token)
        except Exception as exc:
            logger.warning("[AUTH] Keycloak logout call failed: %s", str(exc))

    response.delete_cookie(key="uka_access_token", path="/")
    response.delete_cookie(key="uka_refresh_token", path="/")

    return {
        "status": "success",
        "message": "Logged out successfully",
    }


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Development User Login Entry Point",
    description="Authenticates or provisions a development user in PostgreSQL and returns an access token.",
)
async def login(
    payload: LoginRequest,
    response: Response,
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

    token = f"dev-token-{user.role}-{user.id}"
    response.set_cookie(
        key="uka_access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=3600,
        secure=settings.is_cookie_secure,
        path="/",
    )

    logger.info("User logged in: id=%s email=%s role=%s", user.id, user.email, user.role)
    return LoginResponse(
        user=to_user_response(user),
        access_token=token,
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
