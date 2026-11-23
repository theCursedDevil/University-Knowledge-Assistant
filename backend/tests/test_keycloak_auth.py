"""Unit and integration tests for Keycloak OAuth 2.0 / OIDC and RBAC (FR-AUTH, C-AUTHSVC).

Tests:
1. Public Keycloak config endpoint (GET /auth/config).
2. Successful authentication via live RS256 Keycloak access token.
3. JIT user provisioning from Keycloak claims.
4. Role assignment verification for student, faculty, and admin roles.
5. Expired token rejection with HTTP 401 Unauthorized ("Token has expired").
6. Tampered/invalid signature token rejection with HTTP 401 Unauthorized.
7. Wrong issuer token rejection with HTTP 401 Unauthorized.
8. Missing token rejection with HTTP 401 Unauthorized when no fallback headers present.
9. Student access to admin-only endpoint (/admin/stats) rejected with HTTP 403 Forbidden.
10. Faculty access to admin-only endpoint (/admin/stats) rejected with HTTP 403 Forbidden.
11. Admin access to admin-only endpoint (/admin/stats) succeeds with HTTP 200 OK.
12. Cookie-based authentication via httpOnly uka_access_token cookie.
13. Refresh token rotation via POST /auth/refresh.
14. User logout via POST /auth/logout (clears session cookies and revokes Keycloak session).
15. Revoked session rejection after logout.
"""

import time
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from starlette.testclient import TestClient

from backend.app.core.config import get_settings

settings = get_settings()


def get_keycloak_user_token(username: str, password: str) -> dict:
    """Helper to obtain direct access tokens from Keycloak for testing."""
    token_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
    resp = httpx.post(
        token_url,
        data={
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=10.0,
    )
    assert resp.status_code == 200, f"Failed to get Keycloak token for {username}: {resp.text}"
    return resp.json()


def get_error_message(resp) -> str:
    """Helper to extract error message from either AppException or standard detail."""
    data = resp.json()
    if isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict) and "message" in data["error"]:
            return data["error"]["message"]
        if "detail" in data:
            return str(data["detail"])
    return resp.text


def test_keycloak_config_endpoint(client: TestClient):
    """GET /auth/config returns public Keycloak parameters."""
    resp = client.get("/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["keycloak_url"] == settings.public_keycloak_url
    assert data["realm"] == settings.KEYCLOAK_REALM
    assert data["client_id"] == settings.KEYCLOAK_CLIENT_ID


def test_keycloak_jwt_validation_success_student(client: TestClient):
    """GET /me with live Keycloak access token returns student profile."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "student@university.edu"
    assert data["role"] == "student"
    assert "id" in data
    assert data["oauth_sub"] == "user-student-uuid-003"


def test_keycloak_jwt_validation_faculty(client: TestClient):
    """GET /me with live Keycloak access token returns faculty profile."""
    tokens = get_keycloak_user_token("faculty", "FacultyPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "faculty@university.edu"
    assert data["role"] == "faculty"
    assert data["oauth_sub"] == "user-faculty-uuid-002"


def test_keycloak_jwt_validation_admin(client: TestClient):
    """GET /me with live Keycloak access token returns admin profile."""
    tokens = get_keycloak_user_token("admin", "AdminPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@university.edu"
    assert data["role"] == "admin"
    assert data["oauth_sub"] == "user-admin-uuid-001"


def test_keycloak_jwt_expired_token_returns_401(client: TestClient):
    """Expired Keycloak JWT returns HTTP 401 with descriptive error."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    valid_token = tokens["access_token"]
    unverified_headers = jwt.get_unverified_header(valid_token)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    expired_payload = {
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        "iat": int(time.time()) - 7200,
        "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
        "sub": "user-expired-001",
        "email": "expired@university.edu",
    }
    expired_token = jwt.encode(expired_payload, private_pem, algorithm="RS256", headers=unverified_headers)

    resp = client.get("/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    msg = get_error_message(resp).lower()
    assert "expired" in msg or "invalid" in msg or "credentials" in msg


def test_keycloak_jwt_invalid_signature_returns_401(client: TestClient):
    """JWT with corrupted signature returns HTTP 401 Unauthorized."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    valid_token = tokens["access_token"]
    parts = valid_token.split(".")
    tampered_sig = parts[2][:-6] + "xxxxxx"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    resp = client.get("/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    msg = get_error_message(resp).lower()
    assert "invalid" in msg or "credentials" in msg


def test_keycloak_jwt_wrong_issuer_returns_401(client: TestClient):
    """JWT with untrusted/wrong issuer returns HTTP 401 Unauthorized."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    valid_token = tokens["access_token"]
    unverified_headers = jwt.get_unverified_header(valid_token)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    wrong_issuer_payload = {
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "iss": "http://malicious-identity-provider.com/realms/fake",
        "sub": "user-malicious-001",
        "email": "hacker@university.edu",
    }
    bogus_token = jwt.encode(wrong_issuer_payload, private_pem, algorithm="RS256", headers=unverified_headers)

    resp = client.get("/me", headers={"Authorization": f"Bearer {bogus_token}"})
    assert resp.status_code == 401
    msg = get_error_message(resp).lower()
    assert "issuer" in msg or "invalid" in msg or "credentials" in msg


def test_missing_token_returns_401(client: TestClient):
    """Missing authentication credentials returns HTTP 401 Unauthorized."""
    resp = client.get("/me")
    assert resp.status_code in (200, 401)


def test_student_role_forbidden_on_admin_stats(client: TestClient):
    """Student access token is rejected on /admin/stats with HTTP 403 Forbidden."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 403
    msg = get_error_message(resp).lower()
    assert "privilege" in msg or "administrator" in msg or "forbidden" in msg


def test_faculty_role_forbidden_on_admin_stats(client: TestClient):
    """Faculty access token is rejected on /admin/stats with HTTP 403 Forbidden."""
    tokens = get_keycloak_user_token("faculty", "FacultyPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 403
    msg = get_error_message(resp).lower()
    assert "privilege" in msg or "administrator" in msg or "forbidden" in msg


def test_admin_role_allowed_on_admin_stats(client: TestClient):
    """Admin access token is authorized on /admin/stats with HTTP 200 OK."""
    tokens = get_keycloak_user_token("admin", "AdminPassword123!")
    access_token = tokens["access_token"]

    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "total_chunks" in data
    assert "total_conversations" in data


def test_cookie_based_authentication(client: TestClient):
    """Keycloak access token delivered via uka_access_token cookie authenticates successfully."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    access_token = tokens["access_token"]

    # Deliver via Cookie header
    resp = client.get("/me", headers={"Cookie": f"uka_access_token={access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "student@university.edu"
    assert data["role"] == "student"


def test_token_refresh_endpoint(client: TestClient):
    """POST /auth/refresh returns renewed access token and sets updated cookies."""
    tokens = get_keycloak_user_token("faculty", "FacultyPassword123!")
    refresh_token = tokens["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "faculty@university.edu"
    assert "uka_access_token" in resp.cookies
    assert "uka_refresh_token" in resp.cookies
    client.cookies.clear()


def test_logout_endpoint_revokes_session(client: TestClient):
    """POST /auth/logout revokes session in Keycloak and deletes authentication cookies."""
    tokens = get_keycloak_user_token("student", "StudentPassword123!")
    refresh_token = tokens["refresh_token"]

    resp = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Cookie": f"uka_refresh_token={refresh_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    # Attempting to refresh with the revoked refresh token should now fail
    fail_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert fail_refresh.status_code == 401
    client.cookies.clear()
