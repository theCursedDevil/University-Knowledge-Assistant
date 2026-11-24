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
from fastapi.security import OAuth2AuthorizationCodeBearer
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
        configured_issuer = settings.KEYCLOAK_ISSUER
        self.issuer = (configured_issuer or f"{self.keycloak_url}/realms/{self.realm}").rstrip("/")
        self.audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
        self.expected_client_id = settings.KEYCLOAK_CLIENT_ID
        self.jwks_uri = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
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
                audience=self.audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["exp", "iss", "sub", "aud"],
                },
            )
            # Keycloak's authorized party identifies the client to which the token was issued.
            if payload.get("azp") != self.expected_client_id:
                raise UnauthorizedError("Token was not issued to this application.")
            if not isinstance(payload.get("sub"), str) or not payload["sub"].strip():
                raise UnauthorizedError("Token is missing a valid subject.")
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
    oauth_sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(oauth_sub, str) or not oauth_sub.strip():
        raise UnauthorizedError("Identity provider token is missing a subject.")
    if not isinstance(email, str) or not email.strip():
        raise UnauthorizedError("Identity provider token is missing an email address.")
    if claims.get("email_verified") is False:
        raise UnauthorizedError("Verify your email address with the identity provider before signing in.")

    email = email.strip().lower()
    name = claims.get("name") or claims.get("preferred_username") or email.split("@")[0]
    role = KeycloakTokenValidator.extract_role_from_claims(claims)

    # Bind identities only by immutable provider subject. Never silently attach a new
    # provider identity to an existing account based on an email string.
    stmt = select(User).where(User.oauth_sub == oauth_sub)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        email_stmt = select(User).where(User.email == email)
        email_result = await db.execute(email_stmt)
        if email_result.scalars().first():
            raise UnauthorizedError(
                "An account with this email already exists under a different identity. Contact an administrator to link it."
            )

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
        # Existing application roles are managed through the audited admin API.
        # Do not overwrite an administrator's database change with an older token claim.
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


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
    scopes={
        "openid": "OpenID Connect user identity",
        "profile": "User profile information",
        "email": "User email address",
    },
    auto_error=False,
)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(
        default=None,
        description="OAuth 2.0 Bearer access token. Prefer the httpOnly session cookie.",
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve a user exclusively from a validated Keycloak access token.

    Development identities are intentionally not accepted by this production dependency.
    Tests should use FastAPI dependency_overrides rather than mock headers or tokens.
    """
    raw_token: Optional[str] = None
    if token:
        raw_token = token
    elif authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif request.cookies.get("uka_access_token"):
        raw_token = request.cookies.get("uka_access_token")

    if not raw_token:
        raise UnauthorizedError("Missing authentication token.")

    # Local-only development identities are an explicit opt-in. Never accept these
    # synthetic credentials in testing, staging, or production deployments.
    if raw_token.startswith("dev-token-"):
        if settings.ENVIRONMENT.lower() != "development" or not settings.ENABLE_DEV_AUTH:
            raise UnauthorizedError("Development credentials are disabled.")
        parts = raw_token.split("-")
        if len(parts) < 3 or parts[2] not in ("student", "faculty", "admin"):
            raise UnauthorizedError("Invalid development credentials.")
        role = parts[2]
        user = await get_or_create_dev_user(db=db, role=role)
        request.state.user = user
        request.state.current_user = user
        request.state.user_id = str(user.id)
        return user

    claims = token_validator.validate_token(raw_token)
    user = await get_or_provision_user_from_claims(db=db, claims=claims)
    request.state.user = user
    request.state.current_user = user
    request.state.user_id = str(user.id)
    return user


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
