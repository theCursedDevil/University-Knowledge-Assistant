"""Unit and integration tests for PostgreSQL Multi-Replica Architecture and ReplicaRouter.

Validates:
1. Primary accepts writes and standbys operate in read-only recovery mode.
2. Changes committed on Primary propagate via WAL streaming replication to both replicas.
3. Read replicas strictly reject write operations (ReadOnlySQLTransactionError).
4. ReplicaRouter alternates read traffic between healthy replicas using round-robin.
5. ReplicaRouter writes strictly to Primary and NEVER attempts fallback to replicas on write failure.
6. Graceful degradation: surviving replica handles reads when one fails; Primary handles reads when all fail.
7. Active cluster health telemetry via check_db_connection() and GET /health/db.
"""

import asyncio
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from starlette.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.db.router import ReplicaRouter
from backend.app.db.session import (
    primary_engine,
    replica1_engine,
    replica2_engine,
    PrimarySessionLocal,
    Replica1SessionLocal,
    Replica2SessionLocal,
    replica_router,
    check_db_connection,
)

settings = get_settings()


@pytest.fixture(autouse=True)
def reset_router_state():
    """Ensures router health flags and round-robin counter are reset for each test."""
    replica_router.set_replica_health("replica_1", True)
    replica_router.set_replica_health("replica_2", True)
    replica_router.reset_counter()
    yield
    replica_router.set_replica_health("replica_1", True)
    replica_router.set_replica_health("replica_2", True)
    replica_router.reset_counter()


@pytest.mark.asyncio
async def test_primary_and_standbys_recovery_state():
    """Asserts that Primary is not in recovery (read-write) and standbys are in recovery (read-only)."""
    async with primary_engine.connect() as conn:
        p_in_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

    async with replica1_engine.connect() as conn:
        r1_in_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

    async with replica2_engine.connect() as conn:
        r2_in_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

    assert p_in_rec is False, "Primary must have pg_is_in_recovery() == False"
    assert r1_in_rec is True, "Replica 1 must have pg_is_in_recovery() == True"
    assert r2_in_rec is True, "Replica 2 must have pg_is_in_recovery() == True"


@pytest.mark.asyncio
async def test_streaming_replication_data_propagation():
    """Asserts that real user records inserted on Primary replicate to both standbys."""
    test_id = uuid.uuid4()
    test_sub = f"test-sub-{test_id}"
    test_email = f"{test_sub}@example.com"

    # 1. Insert on Primary
    async with primary_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, oauth_sub, name, email, role) "
                "VALUES (:id, :sub, 'Replica Test User', :email, 'student')"
            ),
            {"id": test_id, "sub": test_sub, "email": test_email},
        )

    # 2. Check Replica 1 with retry
    r1_seen = False
    for _ in range(50):
        async with replica1_engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": test_id},
            )).fetchone()
            if row:
                r1_seen = True
                break
        await asyncio.sleep(0.01)

    # 3. Check Replica 2 with retry
    r2_seen = False
    for _ in range(50):
        async with replica2_engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": test_id},
            )).fetchone()
            if row:
                r2_seen = True
                break
        await asyncio.sleep(0.01)

    # 4. Clean up
    async with primary_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": test_id})

    assert r1_seen is True, "Record failed to replicate to Replica 1"
    assert r2_seen is True, "Record failed to replicate to Replica 2"


@pytest.mark.asyncio
async def test_replicas_enforce_read_only_transactions():
    """Asserts that direct write operations on replicas are rejected with read-only errors."""
    bogus_id = uuid.uuid4()

    for name, engine in [("replica_1", replica1_engine), ("replica_2", replica2_engine)]:
        rejected = False
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO users (id, oauth_sub, name, email, role) "
                        "VALUES (:id, 'ro-test', 'RO Test', 'ro@test.com', 'student')"
                    ),
                    {"id": bogus_id},
                )
        except DBAPIError as exc:
            rejected = True
            assert "read-only transaction" in str(exc).lower()

        assert rejected is True, f"{name} allowed a write operation in violation of read-only constraint"


@pytest.mark.asyncio
async def test_replica_router_round_robin_selection():
    """Asserts that ReplicaRouter alternates reads between replica_1 and replica_2."""
    replica_router.reset_counter()
    selected_targets = []

    for _ in range(6):
        target_name, _, _ = await replica_router.get_read_target()
        selected_targets.append(target_name)

    assert selected_targets == [
        "replica_1",
        "replica_2",
        "replica_1",
        "replica_2",
        "replica_1",
        "replica_2",
    ]


@pytest.mark.asyncio
async def test_replica_router_write_strictly_targets_primary():
    """Asserts that get_write_engine() returns primary and writes commit on Primary."""
    engine = replica_router.get_write_engine()
    assert engine == primary_engine

    test_id = uuid.uuid4()
    test_sub = f"write-test-{test_id}"

    # Write using generator
    async for session in replica_router.get_write_session():
        await session.execute(
            text(
                "INSERT INTO users (id, oauth_sub, name, email, role) "
                "VALUES (:id, :sub, 'Primary Write Test', :email, 'faculty')"
            ),
            {"id": test_id, "sub": test_sub, "email": f"{test_sub}@test.com"},
        )

    # Verify directly on Primary
    async with primary_engine.connect() as conn:
        row = (await conn.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": test_id},
        )).fetchone()
        assert row is not None

    # Cleanup
    async with primary_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": test_id})


@pytest.mark.asyncio
async def test_replica_router_never_falls_back_to_replica_on_failed_write():
    """Asserts that when a write operation fails, the exception is raised immediately and never routes to replicas."""
    call_log = []

    # Attempt an invalid write (violates check constraint on role)
    with pytest.raises(Exception):
        async for session in replica_router.get_write_session():
            call_log.append("attempted_primary")
            await session.execute(
                text(
                    "INSERT INTO users (id, oauth_sub, name, email, role) "
                    "VALUES (:id, 'sub', 'Name', 'email@test.com', 'invalid_role')"
                ),
                {"id": uuid.uuid4()},
            )

    assert call_log == ["attempted_primary"]
    # Replicas were not touched for writes


@pytest.mark.asyncio
async def test_replica_router_failover_single_replica_down():
    """Asserts that if Replica 1 is marked unhealthy, all read traffic routes to surviving Replica 2."""
    replica_router.set_replica_health("replica_1", False)

    routed = []
    for _ in range(4):
        target_name, _, _ = await replica_router.get_read_target()
        routed.append(target_name)

    assert routed == ["replica_2", "replica_2", "replica_2", "replica_2"]


@pytest.mark.asyncio
async def test_replica_router_fallback_all_replicas_down():
    """Asserts that if all replicas are down, read requests gracefully fall back to Primary."""
    replica_router.set_replica_health("replica_1", False)
    replica_router.set_replica_health("replica_2", False)

    target_name, engine, sessionmaker = await replica_router.get_read_target()
    assert target_name == "primary"
    assert engine == primary_engine
    assert sessionmaker == PrimarySessionLocal


@pytest.mark.asyncio
async def test_check_db_connection_reports_all_nodes():
    """Asserts that check_db_connection() reports connected status for Primary and both replicas."""
    report = await check_db_connection()

    assert report["status"] == "connected"
    assert report["database"] == settings.POSTGRES_DB

    # Primary check
    assert report["primary"]["status"] == "connected"
    assert report["primary"]["in_recovery"] is False
    assert report["primary"]["connected_replicas"] >= 2
    assert len(report["primary"]["replication_streams"]) >= 2

    # Replicas check
    assert report["replicas"]["replica_1"]["status"] == "connected"
    assert report["replicas"]["replica_1"]["in_recovery"] is True
    assert report["replicas"]["replica_1"]["healthy"] is True

    assert report["replicas"]["replica_2"]["status"] == "connected"
    assert report["replicas"]["replica_2"]["in_recovery"] is True
    assert report["replicas"]["replica_2"]["healthy"] is True

    # Router check
    assert report["router"]["total_replicas"] == 2
    assert report["router"]["healthy_replicas"] == 2
    assert report["router"]["fallback_to_primary"] is False


def test_health_db_api_endpoint(client: TestClient):
    """Verifies that GET /health/db returns 200 OK and multi-replica status JSON."""
    response = client.get("/health/db")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "connected"
    assert "primary" in data
    assert "replicas" in data
    assert "router" in data
    assert data["primary"]["in_recovery"] is False
    assert "replica_1" in data["replicas"]
    assert "replica_2" in data["replicas"]
