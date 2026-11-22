"""Security, token validation, and Keycloak OAuth 2.0 / OIDC provider (C-AUTHSVC, FR-AUTH).

Implements:
- RS256 JWT signature validation using Keycloak JWKS endpoint.
- exp (expiration) and iss (issuer) claim verification.
- Role-based access control (RBAC) extracting roles: 'admin', 'faculty', 'student'.
- Dual token resolution: Authorization: Bearer header and uka_access_token httpOnly cookie.
- Just-in-time (JIT) provisioning and updating of user records in PostgreSQL.
- Keycloak token exchange (PKCE authorization code flow), refresh, and logout helpers.
- Admin and role-specific dependency guards raising HTTP 401 / 403 appropriately.
"""

import uuid
from typing import Optional, Dict, Any, List
import jwt
from jwt import PyJWKClient, PyJWTError, ExpiredSignatureError, InvalidIssuerError
import httpx
from fastapi import Request, Header, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.errors import UnauthorizedError, ForbiddenError
from backend.app.core.logging import logger
from backend.app.db.session import get_db
from backend.app.db.models import User

settings = get_settings()

DEV_ADMIN_SUB = "dev-keycloak-sub-admin-001"
DEV_STUDENT_SUB = "dev-keycloak-sub-student-001"
DEV_FACULTY_SUB = "dev-keycloak-sub-faculty-001"


class KeycloakTokenValidator:
    """Manages Keycloak JWKS keys and validates RS256 OpenID Connect tokens."""

    def __init__(self, keycloak_url: str, realm: str):
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.issuer = f"{self.keycloak_url}/realms/{self.realm}"
        self.jwks_uri = f"{self.issuer}/protocol/openid-connect/certs"
        self._jwks_client: Optional[PyJWKClient] = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Lazy-loaded, key-cached PyJWKClient for Keycloak certificates."""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.jwks_uri, cache_keys=True)
        return self._jwks_client

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validates the RS256 signature, expiration, and issuer of a Keycloak JWT.

        Args:
            token: Raw JWT access token string.

        Returns:
            Decoded claims payload dictionary.

        Raises:
            UnauthorizedError: If token is expired, invalid, has wrong issuer, or fails verification.
        """
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )
            return payload
        except ExpiredSignatureError as exc:
            logger.warning("[AUTH] Token verification failed: signature expired.")
            raise UnauthorizedError("Token has expired.") from exc
        except InvalidIssuerError as exc:
            logger.warning("[AUTH] Token verification failed: invalid token issuer.")
            raise UnauthorizedError("Invalid token issuer.") from exc
        except PyJWTError as exc:
            logger.warning("[AUTH] Token verification failed: %s", str(exc))
            raise UnauthorizedError("Invalid authentication credentials.") from exc
        except Exception as exc:
            logger.error("[AUTH] Unexpected error during token verification: %s", str(exc))
            raise UnauthorizedError("Authentication verification failed.") from exc

    @staticmethod
    def extract_role_from_claims(payload: Dict[str, Any]) -> str:
        """Determines active application role based on Keycloak realm roles.

        Priority order: admin > faculty > student.
        """
        realm_roles = payload.get("realm_access", {}).get("roles", [])
        if "admin" in realm_roles:
            return "admin"
        if "faculty" in realm_roles:
            return "faculty"
        return "student"


# Singleton instance of Keycloak validator
token_validator = KeycloakTokenValidator(
    keycloak_url=settings.KEYCLOAK_URL,
    realm=settings.KEYCLOAK_REALM,
)


class KeycloakAuthService:
    """Provides client-side Keycloak token exchange, token refresh, and logout."""

    def __init__(self, keycloak_url: str, realm: str, client_id: str):
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.logout_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/logout"

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchanges an authorization code and PKCE code_verifier for JWT tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.token_endpoint, data=data)
            if resp.status_code != 200:
                logger.error("[KEYCLOAK] Token exchange failed: %d - %s", resp.status_code, resp.text)
                raise UnauthorizedError("Failed to exchange authorization code with Keycloak.")
            return resp.json()

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Exchanges a refresh token for new access and refresh tokens."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.token_endpoint, data=data)
            if resp.status_code != 200:
                logger.warning("[KEYCLOAK] Token refresh failed: %d - %s", resp.status_code, resp.text)
                raise UnauthorizedError("Session has expired or refresh token is invalid.")
            return resp.json()

    async def logout(self, refresh_token: str) -> bool:
        """Invalidates the user's session at the Keycloak end_session endpoint."""
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.logout_endpoint, data=data)
            return resp.status_code in (200, 204)


# Singleton instance of Keycloak OIDC service
keycloak_service = KeycloakAuthService(
    keycloak_url=settings.KEYCLOAK_URL,
    realm=settings.KEYCLOAK_REALM,
    client_id=settings.KEYCLOAK_CLIENT_ID,
)


async def get_or_create_dev_user(
    db: AsyncSession,
    role: str = "admin",
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> User:
    """Retrieves or provisions a development user in PostgreSQL for tests."""
    role = role.lower()
    if role not in ("student", "faculty", "admin"):
        role = "admin"

    sub_map = {
        "admin": (DEV_ADMIN_SUB, "System Admin (Dev)", "admin@university.edu"),
        "faculty": (DEV_FACULTY_SUB, "Faculty Member (Dev)", "faculty@university.edu"),
        "student": (DEV_STUDENT_SUB, "Student User (Dev)", "student@university.edu"),
    }
    default_sub, default_name, default_email = sub_map[role]

    target_email = email or default_email
    if email and email != default_email:
        target_sub = f"dev-sub-{email}"
        target_name = name or email.split("@")[0].replace(".", " ").title()
    else:
        target_sub = default_sub
        target_name = name or default_name

    stmt = select(User).where(User.oauth_sub == target_sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid.uuid4(),
            oauth_sub=target_sub,
            name=target_name,
            email=target_email,
            role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_or_provision_user_from_claims(
    db: AsyncSession,
    claims: Dict[str, Any],
) -> User:
    """Provisions or updates a user in PostgreSQL based on validated JWT claims."""
    oauth_sub = claims["sub"]
    email = claims.get("email") or f"{claims.get('preferred_username', oauth_sub)}@university.edu"
    name = claims.get("name") or claims.get("preferred_username") or email.split("@")[0]
    role = KeycloakTokenValidator.extract_role_from_claims(claims)

    # 1. Look up by exact oauth_sub
    stmt = select(User).where(User.oauth_sub == oauth_sub)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # 2. If not found by oauth_sub, look up by email to link existing user record
    if not user:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()

    if not user:
        user = User(
            id=uuid.uuid4(),
            oauth_sub=oauth_sub,
            name=name,
            email=email,
            role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("[AUTH] JIT provisioned user: id=%s sub=%s role=%s email=%s", user.id, user.oauth_sub, user.role, user.email)
    else:
        # Update mutable claims if changed
        mutated = False
        if user.role != role:
            user.role = role
            mutated = True
        if user.name != name:
            user.name = name
            mutated = True
        if user.oauth_sub != oauth_sub:
            user.oauth_sub = oauth_sub
            mutated = True
        if mutated:
            await db.commit()
            await db.refresh(user)

    return user


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(
        default=None,
        description="OAuth 2.0 Bearer access token.",
    ),
    x_dev_role: Optional[str] = Header(
        default=None,
        description="DEVELOPMENT ONLY: Mock role override for local tests.",
    ),
    x_dev_email: Optional[str] = Header(
        default=None,
        description="DEVELOPMENT ONLY: Mock email override for local tests.",
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolves and validates the authenticated user identity.

    Checks:
    1. Authorization: Bearer <token> header.
    2. uka_access_token httpOnly cookie.
    3. If token present:
       - Validates Keycloak RS256 signature, exp, and iss.
       - JIT provisions/updates user record in PostgreSQL.
    4. If no token present:
       - In testing/development mode, falls back to dev headers if provided.
       - Otherwise raises HTTP 401 UnauthorizedError.
    """
    # 1. Authorization: Bearer <token>
    user = None
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
        if raw_token.startswith("dev-token-") and settings.ENVIRONMENT in ("development", "testing"):
            role = "admin"
            if "student" in raw_token:
                role = "student"
            elif "faculty" in raw_token:
                role = "faculty"
            elif "admin" in raw_token:
                role = "admin"
            elif x_dev_role:
                role = x_dev_role.lower()
            user = await get_or_create_dev_user(db=db, role=role, email=x_dev_email)
        else:
            claims = token_validator.validate_token(raw_token)
            user = await get_or_provision_user_from_claims(db=db, claims=claims)

    # 2. Explicit dev override header in development/testing mode
    elif settings.ENVIRONMENT in ("development", "testing") and (x_dev_role is not None or x_dev_email is not None):
        target_role = x_dev_role.lower() if x_dev_role else "admin"
        user = await get_or_create_dev_user(db=db, role=target_role, email=x_dev_email)

    # 3. Cookie-based authentication (uka_access_token httpOnly cookie)
    elif "uka_access_token" in request.cookies:
        cookie_token = request.cookies.get("uka_access_token")
        if cookie_token.startswith("dev-token-") and settings.ENVIRONMENT in ("development", "testing"):
            role = "admin"
            if "student" in cookie_token:
                role = "student"
            elif "faculty" in cookie_token:
                role = "faculty"
            user = await get_or_create_dev_user(db=db, role=role, email=x_dev_email)
        else:
            claims = token_validator.validate_token(cookie_token)
            user = await get_or_provision_user_from_claims(db=db, claims=claims)

    # 4. Default fallback in development/testing mode (e.g. GET /me without headers)
    elif settings.ENVIRONMENT in ("development", "testing"):
        user = await get_or_create_dev_user(db=db, role="admin", email=x_dev_email)

    if user is not None:
        request.state.user = user
        request.state.current_user = user
        request.state.user_id = str(user.id)
        return user

    # Missing credentials in non-dev environment
    raise UnauthorizedError("Missing authentication token.")


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforces administrator role requirement.

    Raises HTTP 403 Forbidden if user is not an administrator.
    """
    if current_user.role != "admin":
        logger.warning(
            "[AUTH] Access denied: User %s with role '%s' attempted admin action.",
            current_user.email,
            current_user.role,
        )
        raise ForbiddenError("Administrator privileges required for this action.")
    return current_user


def require_role(allowed_roles: List[str]):
    """Factory dependency enforcing that the current user possesses one of the allowed roles."""

    async def _role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "[AUTH] Access denied: User %s with role '%s' requires one of %s.",
                current_user.email,
                current_user.role,
                allowed_roles,
            )
            raise ForbiddenError(f"Role in {allowed_roles} required for this action.")
        return current_user

    return _role_guard
