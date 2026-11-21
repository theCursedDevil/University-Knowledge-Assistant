"""Pytest configuration and test client fixtures."""

import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.main import create_app
from backend.app.core.config import get_settings


@pytest.fixture(scope="session")
def app():
    """Builds an application instance for testing."""
    return create_app()


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


