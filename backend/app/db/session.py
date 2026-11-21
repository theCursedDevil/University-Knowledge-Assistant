"""Database connection module and SQLAlchemy session management.

Supports PostgreSQL primary (read-write) and read replicas.
Includes connection check utilities and FastAPI session dependencies.
"""

from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.core.logging import logger

settings = get_settings()

# Asynchronous engine for primary read-write database
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session for request lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """Probes PostgreSQL database connectivity without raising unhandled exceptions.

    Returns a dictionary reporting the connection status.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return {"status": "connected", "database": settings.POSTGRES_DB}
    except Exception as exc:
        logger.warning("Database connection check failed: %s", str(exc))
        return {
            "status": "disconnected",
            "database": settings.POSTGRES_DB,
            "error": str(exc),
        }
