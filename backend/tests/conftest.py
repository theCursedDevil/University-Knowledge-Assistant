"""Pytest configuration and test client fixtures.

Development identities are injected with FastAPI dependency overrides here; the
application's production authentication dependency never trusts X-Dev headers.
"""

import os

# Set test-only configuration before importing application modules that construct engines.
os.environ["ENVIRONMENT"] = "testing"
os.environ["ENABLE_DEV_AUTH"] = "true"

import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.main import create_app
from backend.app.core.config import get_settings
from backend.app.core.security import get_current_user, get_or_create_dev_user
from backend.app.db.models import User
from backend.app.db.session import get_db


@pytest.fixture(scope="session")
def app():
    """Builds an application with test-only identity injection."""
    application = create_app()

    async def test_identity_override(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> User:
        raw_token = request.headers.get("Authorization", "")
        raw_token = raw_token[7:].strip() if raw_token.lower().startswith("bearer ") else request.cookies.get("uka_access_token", "")
        role = request.headers.get("X-Dev-Role", "student").lower().strip()
        email = request.headers.get("X-Dev-Email")
        user = None

        if raw_token.startswith("dev-token-"):
            parts = raw_token.split("-", 3)
            if len(parts) == 4 and parts[2] in ("student", "faculty", "admin"):
                try:
                    import uuid
                    user_id = uuid.UUID(parts[3])
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalars().first()
                    role = parts[2]
                except (ValueError, TypeError):
                    user = None

        if user is None:
            if role not in ("student", "faculty", "admin"):
                role = "student"
            user = await get_or_create_dev_user(db=db, role=role, email=email)

        request.state.user = user
        request.state.current_user = user
        request.state.user_id = str(user.id)
        return user

    application.dependency_overrides[get_current_user] = test_identity_override
    return application


@pytest.fixture(scope="session")
def client(app):
    """Synchronous Starlette/FastAPI TestClient fixture."""
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture(scope="session")
def settings():
    """Provides application settings for assertion checks."""
    return get_settings()


@pytest_asyncio.fixture
async def db_session(settings):
    """Provides an isolated AsyncSession per test using NullPool to avoid cross-loop issues."""
    test_engine = create_async_engine(
        settings.async_database_url,
        poolclass=NullPool,
    )
    test_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with test_session_factory() as session:
        yield session
    await test_engine.dispose()


