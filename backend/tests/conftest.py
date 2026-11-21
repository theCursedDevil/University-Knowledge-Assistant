"""Pytest configuration and test client fixtures."""

import pytest
from starlette.testclient import TestClient

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
