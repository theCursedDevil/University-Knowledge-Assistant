"""PostgreSQL Multi-Replica Router module.

Implements round-robin read load balancing across PostgreSQL read replicas with
strict primary-only write routing, health tracking, and graceful fallback to
primary for reads when replicas are unavailable.
"""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text

from backend.app.core.logging import logger


class ReplicaRouter:
    """Manages routing between PostgreSQL Primary and Read Replicas (C-ROUTER / C-DAL).

    Guarantees:
    1. Write operations are routed strictly and exclusively to the Primary.
    2. Read operations are distributed across healthy replicas via round-robin.
    3. If all replicas become unavailable, reads gracefully fall back to Primary.
    4. Failed writes NEVER fall back to a replica.
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
    # Read Routing (Round-Robin with Graceful Fallback)
    # --------------------------------------------------------------------------

    async def get_read_target(self) -> Tuple[str, AsyncEngine, async_sessionmaker[AsyncSession]]:
        """Selects the next database engine and sessionmaker for read operations.

        Uses round-robin across healthy replicas. If no replicas are healthy,
        gracefully falls back to the Primary.
        """
        async with self._lock:
            # Filter healthy replicas
            healthy_names = [
                name for name in self._replica_names
                if self._replica_health.get(name, False)
            ]

            if healthy_names:
                # Round-robin selection
                selected_name = healthy_names[self._rr_counter % len(healthy_names)]
                self._rr_counter = (self._rr_counter + 1) % 1_000_000
                engine = self.replica_engines[selected_name]
                sm = self.replica_sessionmakers[selected_name]
                return selected_name, engine, sm

            # Fallback to Primary when all replicas are down
            logger.warning(
                "All read replicas %s are currently marked unhealthy. "
                "Gracefully routing read operation to Primary database.",
                self._replica_names,
            )
            return "primary", self.primary_engine, self.primary_sessionmaker

    async def get_read_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency / generator yielding an async read session.

        Routes read requests across healthy replicas via round-robin,
        falling back to Primary if all replicas are down.
        """
        target_name, _, sessionmaker = await self.get_read_target()
        async with sessionmaker() as session:
            try:
                yield session
            except Exception as exc:
                # If an error occurs on a replica during read, record error and mark unhealthy
                if target_name in self._replica_health:
                    logger.warning(
                        "Read query failed on replica '%s': %s. Marking replica unhealthy.",
                        target_name,
                        exc,
                    )
                    self._replica_health[target_name] = False
                    self._replica_last_error[target_name] = str(exc)
                raise
            finally:
                await session.close()

    # --------------------------------------------------------------------------
    # Health Checks and Observability
    # --------------------------------------------------------------------------

    async def check_health(self) -> Dict[str, Any]:
        """Performs active connection and replication health checks across all nodes.

        Probes:
        1. Primary: checks connectivity, confirms in_recovery=False, and retrieves pg_stat_replication.
        2. Each replica: checks connectivity and confirms in_recovery=True (standby mode).

        Updates internal healthy status flags accordingly.
        """
        report: Dict[str, Any] = {
            "status": "connected",
            "database": self.primary_engine.url.database or "university_assistant",
            "primary": {"status": "unknown"},
            "replicas": {},
            "router": {
                "total_replicas": len(self._replica_names),
                "healthy_replicas": 0,
                "fallback_to_primary": False,
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
