"""Database connection module and SQLAlchemy session management.

Supports PostgreSQL primary (read-write) and read replicas using ReplicaRouter (C-ROUTER / C-DAL).
Provides session dependencies for write and read operations, connection health checks,
and multi-engine connection pooling.
"""

from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from backend.app.core.config import get_settings
from backend.app.db.router import ReplicaRouter

settings = get_settings()

# Engine connection pool selection
# NullPool is used in testing/dev to ensure each coroutine owns its asyncpg connection
pool_class = NullPool if settings.ENVIRONMENT in ("testing", "development") else AsyncAdaptedQueuePool

engine_kwargs = {"echo": False, "poolclass": pool_class}
if pool_class is AsyncAdaptedQueuePool:
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True})

# 1. Primary Engine (Read-Write)
primary_engine: AsyncEngine = create_async_engine(
    settings.primary_async_url,
    **engine_kwargs,
)

# 2. Read Replica 1 Engine (Read-Only)
replica1_engine: AsyncEngine = create_async_engine(
    settings.replica1_async_url,
    **engine_kwargs,
)

# 3. Read Replica 2 Engine (Read-Only)
replica2_engine: AsyncEngine = create_async_engine(
    settings.replica2_async_url,
    **engine_kwargs,
)

# Engine alias for backward compatibility with Alembic and legacy callers
engine: AsyncEngine = primary_engine

# Session factories
PrimarySessionLocal = async_sessionmaker(
    bind=primary_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

Replica1SessionLocal = async_sessionmaker(
    bind=replica1_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

Replica2SessionLocal = async_sessionmaker(
    bind=replica2_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

# AsyncSessionLocal alias for backward compatibility
AsyncSessionLocal = PrimarySessionLocal

# Instantiate multi-replica router singleton
replica_router = ReplicaRouter(
    primary_engine=primary_engine,
    replica_engines={
        "replica_1": replica1_engine,
        "replica_2": replica2_engine,
    },
    primary_sessionmaker=PrimarySessionLocal,
    replica_sessionmakers={
        "replica_1": Replica1SessionLocal,
        "replica_2": Replica2SessionLocal,
    },
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async write session bound to Primary.

    Maintains backward compatibility with all existing routes and tests.
    """
    async for session in replica_router.get_write_session():
        yield session


async def get_write_db() -> AsyncGenerator[AsyncSession, None]:
    """Explicit alias for primary write database session."""
    async for session in replica_router.get_write_session():
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a read session balanced across replicas (or primary fallback)."""
    async for session in replica_router.get_read_session():
        yield session


async def check_db_connection() -> Dict[str, Any]:
    """Probes PostgreSQL primary and read replicas, reporting cluster health and replication status."""
    return await replica_router.check_health()
