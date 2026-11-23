"""PostgreSQL Multi-Replica Router module.

Implements:
1. Round-robin read load balancing across healthy PostgreSQL read replicas.
2. Read-Your-Own-Writes consistency window routing to Primary (FR-DBSYNC-003, C-ROUTER).
3. Strict primary-only write routing (failed writes NEVER fall back to replicas).
4. Graceful fallback to Primary when all replicas are unavailable.
5. Cluster health and WAL streaming replication observability.
"""

import asyncio
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text

try:
    import redis
except ImportError:
    redis = None

from backend.app.core.config import get_settings
from backend.app.core.logging import logger

settings = get_settings()


class ReadTarget(tuple):
    """3-tuple representing database target (name, engine, sessionmaker) with reason attribute."""

    def __new__(
        cls,
        name: str,
        engine: AsyncEngine,
        sessionmaker: async_sessionmaker[AsyncSession],
        reason: str = "round-robin",
    ):
        return super().__new__(cls, (name, engine, sessionmaker))

    def __init__(
        self,
        name: str,
        engine: AsyncEngine,
        sessionmaker: async_sessionmaker[AsyncSession],
        reason: str = "round-robin",
    ):
        self.name = name
        self.engine = engine
        self.sessionmaker = sessionmaker
        self.reason = reason


class ReplicaRouter:
    """Manages routing between PostgreSQL Primary and Read Replicas (C-ROUTER / C-DAL).

    Guarantees:
    1. Write operations are routed strictly and exclusively to the Primary.
    2. Read-your-own-writes: subsequent reads from a user who recently performed a write
       are routed to Primary during a configurable session window (FR-DBSYNC-003).
    3. Normal reads are distributed across healthy replicas via round-robin.
    4. If all replicas become unavailable, reads gracefully fall back to Primary.
    5. Failed writes NEVER fall back to a replica.
    """

    def __init__(
        self,
        primary_engine: AsyncEngine,
        replica_engines: Dict[str, AsyncEngine],
        primary_sessionmaker: async_sessionmaker[AsyncSession],
        replica_sessionmakers: Dict[str, async_sessionmaker[AsyncSession]],
    ) -> None:
        self.primary_engine = primary_engine
        self.replica_engines = replica_engines
        self.primary_sessionmaker = primary_sessionmaker
        self.replica_sessionmakers = replica_sessionmakers

        self._replica_names: List[str] = list(replica_engines.keys())
        self._replica_health: Dict[str, bool] = {name: True for name in self._replica_names}
        self._replica_last_error: Dict[str, Optional[str]] = {name: None for name in self._replica_names}
        self._rr_counter: int = 0
        self._lock = asyncio.Lock()

        # Read-your-own-writes session window tracking
        self._user_write_windows: Dict[str, float] = {}  # user_id -> monotonic expiry
        self._redis_client: Optional[Any] = None
        self._init_redis()

    def _init_redis(self) -> None:
        """Initializes Redis client for distributed session window tracking if available."""
        if redis is None:
            return
        try:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=1.0,
            )
            client.ping()
            self._redis_client = client
            logger.info("Connected to Redis for distributed read-your-own-writes session tracking.")
        except Exception as exc:
            logger.info("Redis not available for read-your-own-writes (%s); using in-memory monotonic window tracking.", exc)
            self._redis_client = None

    # --------------------------------------------------------------------------
    # Read-Your-Own-Writes Session Tracking (FR-DBSYNC-003)
    # --------------------------------------------------------------------------

    def record_user_write(
        self,
        user_id: Union[uuid.UUID, str, Any],
        window_seconds: Optional[float] = None,
        secondary_id: Optional[str] = None,
    ) -> None:
        """Records that a user has performed a database write.

        Subsequent reads from this user will route to Primary for the duration
        of window_seconds (default: settings.READ_YOUR_WRITES_WINDOW_SECONDS).
        """
        if not user_id:
            return

        uids = set()
        if hasattr(user_id, "id"):
            uids.add(str(user_id.id))
        if hasattr(user_id, "email") and user_id.email:
            uids.add(str(user_id.email))
        if isinstance(user_id, (str, uuid.UUID)):
            uids.add(str(user_id))
        if secondary_id:
            uids.add(str(secondary_id))

        duration = (
            window_seconds
            if window_seconds is not None
            else settings.READ_YOUR_WRITES_WINDOW_SECONDS
        )

        for uid in uids:
            # 1. In-memory monotonic clock
            self._user_write_windows[uid] = time.monotonic() + duration

            # 2. Redis distributed key
            if self._redis_client:
                try:
                    key = f"uka:user_write_window:{uid}"
                    ms = max(50, int(duration * 1000))
                    self._redis_client.set(key, str(time.time()), px=ms)
                except Exception as exc:
                    logger.warning("Failed to record user write window in Redis: %s", exc)

    def is_in_write_window(self, user_id: Optional[Union[uuid.UUID, str]]) -> bool:
        """Checks whether the user is within their active read-your-own-writes window."""
        if not user_id:
            return False
        uid = str(user_id)

        # 1. In-memory monotonic check
        expiry = self._user_write_windows.get(uid)
        if expiry is not None:
            if time.monotonic() < expiry:
                return True
            else:
                self._user_write_windows.pop(uid, None)

        # 2. Redis check
        if self._redis_client:
            try:
                key = f"uka:user_write_window:{uid}"
                if self._redis_client.exists(key):
                    return True
            except Exception as exc:
                logger.warning("Failed to check write window in Redis: %s", exc)

        return False

    def clear_user_write_window(self, user_id: Union[uuid.UUID, str]) -> None:
        """Clears the write window for a user (used for testing and immediate resets)."""
        uid = str(user_id)
        self._user_write_windows.pop(uid, None)
        if self._redis_client:
            try:
                self._redis_client.delete(f"uka:user_write_window:{uid}")
            except Exception:
                pass

    def clear_all_write_windows(self) -> None:
        """Clears all active write windows."""
        self._user_write_windows.clear()
        if self._redis_client:
            try:
                keys = self._redis_client.keys("uka:user_write_window:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Write Routing (Strictly Primary Only)
    # --------------------------------------------------------------------------

    def get_write_engine(self) -> AsyncEngine:
        """Returns the primary engine for write operations.

        Strictly returns Primary. Replicas are never returned for writes.
        """
        return self.primary_engine

    async def get_write_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency / generator yielding a write session bound to Primary.

        Never falls back to a replica if a write fails.
        """
        async with self.primary_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # --------------------------------------------------------------------------
    # Read Routing (Round-Robin with Read-Your-Own-Writes and Primary Fallback)
    # --------------------------------------------------------------------------

    async def get_read_target(
        self,
        user_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> ReadTarget:
        """Selects the target database engine and sessionmaker for read operations.

        Routing hierarchy:
        1. If user recently wrote data within the session window: Primary (read-your-own-writes).
        2. If replicas are healthy: Round-robin across healthy replicas.
        3. If all replicas are down: Primary (graceful fallback).
        """
        # 1. Read-Your-Own-Writes consistency
        if user_id and self.is_in_write_window(user_id):
            logger.info(
                "User '%s' is within active read-after-write window (%.1fs). Routing read to Primary.",
                user_id,
                settings.READ_YOUR_WRITES_WINDOW_SECONDS,
            )
            return ReadTarget(
                "primary",
                self.primary_engine,
                self.primary_sessionmaker,
                reason="read-your-own-writes",
            )

        # 2. Round-Robin replica balancing
        async with self._lock:
            healthy_names = [
                name for name in self._replica_names
                if self._replica_health.get(name, False)
            ]

            if healthy_names:
                selected_name = healthy_names[self._rr_counter % len(healthy_names)]
                self._rr_counter = (self._rr_counter + 1) % 1_000_000
                engine = self.replica_engines[selected_name]
                sm = self.replica_sessionmakers[selected_name]
                return ReadTarget(
                    selected_name,
                    engine,
                    sm,
                    reason="round-robin",
                )

            # 3. Fallback to Primary when all replicas are down
            logger.warning(
                "All read replicas %s are currently marked unhealthy. "
                "Gracefully routing read operation to Primary database.",
                self._replica_names,
            )
            return ReadTarget(
                "primary",
                self.primary_engine,
                self.primary_sessionmaker,
                reason="all-replicas-unhealthy-fallback",
            )

    async def get_read_session(
        self,
        user_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency / generator yielding an async read session."""
        target = await self.get_read_target(user_id=user_id)
        async with target.sessionmaker() as session:
            try:
                yield session
            except Exception as exc:
                if target.name in self._replica_health:
                    logger.warning(
                        "Read query failed on replica '%s': %s. Marking replica unhealthy.",
                        target.name,
                        exc,
                    )
                    self._replica_health[target.name] = False
                    self._replica_last_error[target.name] = str(exc)
                raise
            finally:
                await session.close()

    # --------------------------------------------------------------------------
    # Health Checks and Observability
    # --------------------------------------------------------------------------

    async def check_health(self) -> Dict[str, Any]:
        """Performs active connection and replication health checks across all nodes."""
        report: Dict[str, Any] = {
            "status": "connected",
            "database": self.primary_engine.url.database or "university_assistant",
            "primary": {"status": "unknown"},
            "replicas": {},
            "router": {
                "total_replicas": len(self._replica_names),
                "healthy_replicas": 0,
                "fallback_to_primary": False,
                "active_write_windows": len(self._user_write_windows),
            },
        }

        # 1. Probe Primary
        try:
            async with self.primary_engine.connect() as conn:
                res = await conn.execute(text("SELECT pg_is_in_recovery()"))
                in_recovery = res.scalar()

                # Query replication status
                repl_rows = await conn.execute(text(
                    "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn, sync_state, application_name "
                    "FROM pg_stat_replication"
                ))
                replication_info = [
                    {
                        "client_addr": str(row.client_addr),
                        "state": row.state,
                        "sent_lsn": str(row.sent_lsn),
                        "replay_lsn": str(row.replay_lsn),
                        "sync_state": row.sync_state,
                        "application_name": row.application_name,
                    }
                    for row in repl_rows.fetchall()
                ]

                report["primary"] = {
                    "status": "connected",
                    "in_recovery": in_recovery,
                    "connected_replicas": len(replication_info),
                    "replication_streams": replication_info,
                }
        except Exception as exc:
            logger.error("Health check failed on Primary: %s", exc)
            report["primary"] = {
                "status": "error",
                "error": str(exc),
            }
            report["status"] = "disconnected"

        # 2. Probe Replicas
        healthy_count = 0
        for name in self._replica_names:
            engine = self.replica_engines[name]
            try:
                async with engine.connect() as conn:
                    res = await conn.execute(text("SELECT pg_is_in_recovery()"))
                    in_recovery = res.scalar()
                    self._replica_health[name] = True
                    self._replica_last_error[name] = None
                    healthy_count += 1
                    report["replicas"][name] = {
                        "status": "connected",
                        "in_recovery": in_recovery,
                        "healthy": True,
                    }
            except Exception as exc:
                logger.warning("Health check failed on replica '%s': %s", name, exc)
                self._replica_health[name] = False
                self._replica_last_error[name] = str(exc)
                report["replicas"][name] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(exc),
                }

        report["router"]["healthy_replicas"] = healthy_count
        if healthy_count == 0:
            report["router"]["fallback_to_primary"] = True
            if report["primary"].get("status") != "connected":
                report["status"] = "disconnected"

        return report

    # --------------------------------------------------------------------------
    # Test Utilities
    # --------------------------------------------------------------------------

    def set_replica_health(self, name: str, healthy: bool) -> None:
        """Manually overrides replica health flag for testing failover scenarios."""
        if name in self._replica_health:
            self._replica_health[name] = healthy

    def get_replica_health(self) -> Dict[str, bool]:
        """Returns the current health status of all managed replicas."""
        return dict(self._replica_health)

    def reset_counter(self) -> None:
        """Resets the round-robin counter to 0."""
        self._rr_counter = 0
