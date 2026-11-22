"""Development authentication compatibility module.

Delegates to backend.app.core.security while maintaining backwards compatibility
with Phase 3-7 routers and test suites.
"""

from backend.app.core.security import (
    DEV_ADMIN_SUB,
    DEV_STUDENT_SUB,
    DEV_FACULTY_SUB,
    get_or_create_dev_user,
    get_current_user,
    require_admin,
    require_role,
    KeycloakTokenValidator,
    KeycloakAuthService,
    token_validator,
    keycloak_service,
)

__all__ = [
    "DEV_ADMIN_SUB",
    "DEV_STUDENT_SUB",
    "DEV_FACULTY_SUB",
    "get_or_create_dev_user",
    "get_current_user",
    "require_admin",
    "require_role",
    "KeycloakTokenValidator",
    "KeycloakAuthService",
    "token_validator",
    "keycloak_service",
]
