"""Development-only authentication and role-based access control (RBAC) provider.

==============================================================================
WARNING: DEVELOPMENT-ONLY AUTHENTICATION STUB
This module provides a controlled mock identity for local testing and initial
API development prior to Phase 8 Keycloak OAuth 2.0 / OIDC integration.
DO NOT USE IN PRODUCTION.
==============================================================================
"""

import uuid
from typing import Optional
from fastapi import Header, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.errors import ForbiddenError, UnauthorizedError
from backend.app.core.logging import logger
from backend.app.db.session import get_db
from backend.app.db.models import User

settings = get_settings()

DEV_ADMIN_SUB = "dev-keycloak-sub-admin-001"
DEV_STUDENT_SUB = "dev-keycloak-sub-student-001"
DEV_FACULTY_SUB = "dev-keycloak-sub-faculty-001"


async def get_or_create_dev_user(
    db: AsyncSession,
    role: str = "admin",
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> User:
    """Retrieves or provisions a persistent development user in PostgreSQL."""
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
        logger.info(
            "[DEV-AUTH] Provisioned initial development user: id=%s role=%s email=%s",
            user.id,
            user.role,
            user.email,
        )

    return user


async def get_current_user(
    x_dev_role: Optional[str] = Header(
        default=None,
        description="DEVELOPMENT ONLY: Override active role ('admin', 'faculty', 'student').",
    ),
    x_dev_email: Optional[str] = Header(
        default=None,
        description="DEVELOPMENT ONLY: Override active user email.",
    ),
    authorization: Optional[str] = Header(
        default=None,
        description="DEVELOPMENT ONLY: Bearer token (e.g. 'Bearer dev-admin-token' or 'Bearer dev-student-token').",
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Development identity resolver.

    Resolves the current user from headers or defaults to dev admin.
    """
    if settings.ENVIRONMENT != "development" and settings.ENVIRONMENT != "testing":
        # In non-dev environments, stub is rejected until Keycloak is integrated
        raise UnauthorizedError("Keycloak OIDC authentication required.")

    role = "admin"
    if x_dev_role:
        role = x_dev_role.lower()
    elif authorization:
        token = authorization.replace("Bearer ", "").strip()
        if "student" in token:
            role = "student"
        elif "faculty" in token:
            role = "faculty"
        elif "admin" in token:
            role = "admin"

    return await get_or_create_dev_user(db=db, role=role, email=x_dev_email)


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforces administrator role requirement.

    Raises HTTP 403 Forbidden if user is not an administrator.
    """
    if current_user.role != "admin":
        logger.warning(
            "[DEV-AUTH] Access denied: User %s with role '%s' attempted admin action.",
            current_user.email,
            current_user.role,
        )
        raise ForbiddenError("Administrator privileges required for this action.")
    return current_user
