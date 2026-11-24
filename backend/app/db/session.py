"""Database connection module and SQLAlchemy session management.

Supports PostgreSQL primary (read-write) and read replicas using ReplicaRouter (C-ROUTER / C-DAL).
Provides session dependencies for write and read operations, connection health checks,
read-your-own-writes consistency routing (FR-DBSYNC-003), and multi-engine connection pooling.
"""

from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy.exc import DBAPIError, OperationalError

from backend.app.core.config import get_settings
from backend.app.db.router import ReplicaRouter

settings = get_settings()

# Engine connection pool selection
# NullPool is used in testing/dev to ensure each coroutine owns its asyncpg connection
pool_class = NullPool if settings.ENVIRONMENT == "testing" else AsyncAdaptedQueuePool

engine_kwargs = {"echo": False, "poolclass": pool_class}
if pool_class is AsyncAdaptedQueuePool:
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True})

# 1. Primary Engine (Read-Write)
primary_engine: AsyncEngine = create_async_engine(
    settings.primary_async_url,
    **engine_kwargs,
)

# 2. Read Replica Engines. Laptop/demo mode reuses the primary engine and does not
# allocate extra connection pools for replicas that are not running.
if settings.DB_READ_REPLICAS_ENABLED:
    replica1_engine: AsyncEngine = create_async_engine(
        settings.replica1_async_url,
        **engine_kwargs,
    )
    replica2_engine: AsyncEngine = create_async_engine(
        settings.replica2_async_url,
        **engine_kwargs,
    )
else:
    replica1_engine = primary_engine
    replica2_engine = primary_engine

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
    replica_engines=(
        {
            "replica_1": replica1_engine,
            "replica_2": replica2_engine,
        }
        if settings.DB_READ_REPLICAS_ENABLED
        else {}
    ),
    primary_sessionmaker=PrimarySessionLocal,
    replica_sessionmakers=(
        {
            "replica_1": Replica1SessionLocal,
            "replica_2": Replica2SessionLocal,
        }
        if settings.DB_READ_REPLICAS_ENABLED
        else {}
    ),
)


def resolve_user_id_from_request(request: Optional[Request]) -> Optional[str]:
    """Resolve a user ID only from trusted state set by authenticated middleware."""
    if request is None:
        return None
    user_state = getattr(request.state, "user", None) or getattr(request.state, "current_user", None)
    if user_state and getattr(user_state, "id", None):
        return str(user_state.id)
    user_id = getattr(request.state, "user_id", None)
    return str(user_id) if user_id else None


async def get_db(
    request: Request = None,
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async write session bound to Primary.

    Maintains backward compatibility with all existing routes and tests.
    """
    if request is not None:
        request.state.db_route = "primary"
        request.state.db_route_reason = "write"
    async for session in replica_router.get_write_session():
        yield session


async def get_write_db(
    request: Request = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Explicit alias for primary write database session."""
    if request is not None:
        request.state.db_route = "primary"
        request.state.db_route_reason = "write"
    async for session in replica_router.get_write_session():
        yield session


async def get_read_db(
    request: Request = None,
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a read session.

    If the user has recently written data (within the read-your-own-writes session window),
    routes to Primary. Otherwise balances across healthy replicas via round-robin.
    """
    user_id = resolve_user_id_from_request(request) if request is not None else None
    target = await replica_router.get_read_target(user_id=user_id)

    if request is not None:
        request.state.db_route = target.name
        request.state.db_route_reason = target.reason

    async with target.sessionmaker() as session:
        try:
            yield session
        except DBAPIError as exc:
            if target.name in replica_router._replica_health and (
                exc.connection_invalidated or isinstance(exc, OperationalError)
            ):
                replica_router._replica_health[target.name] = False
                replica_router._replica_last_error[target.name] = type(exc).__name__
            raise
        finally:
            await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """Probes PostgreSQL primary and read replicas, reporting cluster health and replication status."""
    return await replica_router.check_health()
