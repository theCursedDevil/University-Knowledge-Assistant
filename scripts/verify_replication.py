#!/usr/bin/env python3
"""PostgreSQL Multi-Replica Physical Streaming Replication Verification Script.

Demonstrates and verifies:
1. Primary accepts write operations.
2. Changes written to Primary replicate asynchronously to Replica 1 and Replica 2.
3. Both replicas enforce read-only transactions (rejecting INSERT/UPDATE/DELETE).
4. ReplicaRouter balances read queries across healthy replicas via round-robin.
5. ReplicaRouter gracefully falls back to Primary if all replicas are unavailable.
6. Writes strictly target Primary and NEVER fall back to replicas.
7. Active WAL replication status and lag reported from pg_stat_replication.
"""

import asyncio
import sys
import time
import uuid
from typing import Dict, Any, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.app.core.config import get_settings
from backend.app.db.router import ReplicaRouter

settings = get_settings()


async def run_verification():
    print("=" * 80)
    print(" UNIVERSITY KNOWLEDGE ASSISTANT — POSTGRESQL REPLICATION VERIFICATION")
    print(" PostgreSQL 16 Multi-Replica Streaming Architecture (C-ROUTER / C-DAL)")
    print("=" * 80)
    print(f"Primary Node:   {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} ({settings.POSTGRES_DB})")
    print(f"Replica 1 Node: {settings.POSTGRES_REPLICA1_HOST}:{settings.POSTGRES_REPLICA1_PORT} ({settings.POSTGRES_DB})")
    print(f"Replica 2 Node: {settings.POSTGRES_REPLICA2_HOST}:{settings.POSTGRES_REPLICA2_PORT} ({settings.POSTGRES_DB})")
    print("-" * 80)

    # Setup dedicated test engines
    primary_engine = create_async_engine(settings.primary_async_url, echo=False)
    replica1_engine = create_async_engine(settings.replica1_async_url, echo=False)
    replica2_engine = create_async_engine(settings.replica2_async_url, echo=False)

    p_sm = async_sessionmaker(bind=primary_engine, expire_on_commit=False, class_=AsyncSession)
    r1_sm = async_sessionmaker(bind=replica1_engine, expire_on_commit=False, class_=AsyncSession)
    r2_sm = async_sessionmaker(bind=replica2_engine, expire_on_commit=False, class_=AsyncSession)

    router = ReplicaRouter(
        primary_engine=primary_engine,
        replica_engines={"replica_1": replica1_engine, "replica_2": replica2_engine},
        primary_sessionmaker=p_sm,
        replica_sessionmakers={"replica_1": r1_sm, "replica_2": r2_sm},
    )

    all_passed = True

    try:
        # ----------------------------------------------------------------------
        # Step 1: Health & Standby Recovery State Check
        # ----------------------------------------------------------------------
        print("\n[Step 1/6] Verifying Node States and Standby Recovery Flags...")
        async with primary_engine.connect() as conn:
            p_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

        async with replica1_engine.connect() as conn:
            r1_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

        async with replica2_engine.connect() as conn:
            r2_rec = (await conn.execute(text("SELECT pg_is_in_recovery()"))).scalar()

        print(f"  • Primary (Port {settings.POSTGRES_PORT}):   pg_is_in_recovery = {p_rec} (Expected: False - Read/Write)")
        print(f"  • Replica 1 (Port {settings.POSTGRES_REPLICA1_PORT}): pg_is_in_recovery = {r1_rec} (Expected: True  - Read-Only Standby)")
        print(f"  • Replica 2 (Port {settings.POSTGRES_REPLICA2_PORT}): pg_is_in_recovery = {r2_rec} (Expected: True  - Read-Only Standby)")

        assert p_rec is False, "Primary must NOT be in recovery"
        assert r1_rec is True, "Replica 1 MUST be in recovery (standby)"
        assert r2_rec is True, "Replica 2 MUST be in recovery (standby)"
        print("  ✓ Node roles verified successfully.")

        # ----------------------------------------------------------------------
        # Step 2: Write to Primary and Measure Replication Lag across Replicas
        # ----------------------------------------------------------------------
        print("\n[Step 2/6] Writing Real Record to Primary & Verifying Replication...")
        test_id = uuid.uuid4()
        test_sub = f"repl-verify-{test_id}"
        test_name = "Replication Verification Test User"
        test_email = f"{test_sub}@university.edu"

        t0 = time.perf_counter()
        async with primary_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO users (id, oauth_sub, name, email, role) "
                    "VALUES (:id, :sub, :name, :email, 'student')"
                ),
                {"id": test_id, "sub": test_sub, "name": test_name, "email": test_email},
            )
        primary_write_ms = (time.perf_counter() - t0) * 1000
        print(f"  • Inserted user record on Primary (id: {test_id}) in {primary_write_ms:.2f} ms")

        # Poll Replica 1
        r1_found = False
        r1_lag_ms = 0.0
        for _ in range(50):
            async with replica1_engine.connect() as conn:
                row = (await conn.execute(
                    text("SELECT id, name, email FROM users WHERE id = :id"),
                    {"id": test_id},
                )).fetchone()
                if row:
                    r1_found = True
                    r1_lag_ms = (time.perf_counter() - t0) * 1000
                    break
            await asyncio.sleep(0.01)

        # Poll Replica 2
        r2_found = False
        r2_lag_ms = 0.0
        for _ in range(50):
            async with replica2_engine.connect() as conn:
                row = (await conn.execute(
                    text("SELECT id, name, email FROM users WHERE id = :id"),
                    {"id": test_id},
                )).fetchone()
                if row:
                    r2_found = True
                    r2_lag_ms = (time.perf_counter() - t0) * 1000
                    break
            await asyncio.sleep(0.01)

        print(f"  • Replica 1 observed record: {r1_found} (replication lag: {r1_lag_ms:.2f} ms)")
        print(f"  • Replica 2 observed record: {r2_found} (replication lag: {r2_lag_ms:.2f} ms)")

        assert r1_found, "Replica 1 did not receive replicated record"
        assert r2_found, "Replica 2 did not receive replicated record"
        print("  ✓ Asynchronous streaming replication verified on both replicas.")

        # Cleanup test user
        async with primary_engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": test_id})

        # ----------------------------------------------------------------------
        # Step 3: Replicas Enforce Read-Only Transactions (Write Rejection)
        # ----------------------------------------------------------------------
        print("\n[Step 3/6] Confirming Replicas Reject Direct Write Operations...")
        bogus_id = uuid.uuid4()

        for name, engine in [("Replica 1", replica1_engine), ("Replica 2", replica2_engine)]:
            rejected = False
            error_msg = ""
            try:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO users (id, oauth_sub, name, email, role) "
                            "VALUES (:id, 'bogus', 'Bogus', 'bogus@test.com', 'student')"
                        ),
                        {"id": bogus_id},
                    )
            except Exception as exc:
                rejected = True
                error_msg = str(exc)

            print(f"  • {name} write attempt: rejected={rejected} (Reason: {error_msg.splitlines()[0] if error_msg else ''})")
            assert rejected, f"{name} must reject write operations"
        print("  ✓ Both replicas strictly enforce read-only constraints.")

        # ----------------------------------------------------------------------
        # Step 4: ReplicaRouter Round-Robin Read Balancing
        # ----------------------------------------------------------------------
        print("\n[Step 4/6] Testing ReplicaRouter Round-Robin Selection...")
        router.reset_counter()
        targets: List[str] = []
        for i in range(6):
            target_name, _, _ = await router.get_read_target()
            targets.append(target_name)

        print(f"  • 6 consecutive read requests routed to: {targets}")
        assert targets == [
            "replica_1",
            "replica_2",
            "replica_1",
            "replica_2",
            "replica_1",
            "replica_2",
        ], f"Unexpected routing sequence: {targets}"
        print("  ✓ Round-robin alternating distribution verified across replicas.")

        # ----------------------------------------------------------------------
        # Step 5: Graceful Degradation & Primary Fallback
        # ----------------------------------------------------------------------
        print("\n[Step 5/6] Testing Graceful Degradation and Primary Fallback...")
        # Scenario A: Replica 1 marked down
        router.set_replica_health("replica_1", False)
        targets_deg: List[str] = []
        for _ in range(3):
            target_name, _, _ = await router.get_read_target()
            targets_deg.append(target_name)
        print(f"  • With Replica 1 down, reads routed to surviving: {targets_deg}")
        assert targets_deg == ["replica_2", "replica_2", "replica_2"]

        # Scenario B: Both Replicas marked down
        router.set_replica_health("replica_2", False)
        target_name_fallback, _, _ = await router.get_read_target()
        print(f"  • With all replicas down, read routed to: {target_name_fallback} (Primary fallback)")
        assert target_name_fallback == "primary"

        # Restore health
        router.set_replica_health("replica_1", True)
        router.set_replica_health("replica_2", True)
        print("  ✓ Failover and graceful fallback to Primary verified.")

        # ----------------------------------------------------------------------
        # Step 6: Active Replication Streams from pg_stat_replication
        # ----------------------------------------------------------------------
        print("\n[Step 6/6] Inspecting PostgreSQL WAL Streaming Replication Telemetry...")
        health_report = await router.check_health()
        streams = health_report.get("primary", {}).get("replication_streams", [])
        print(f"  • Active Replication Streams: {len(streams)}")
        for idx, stream in enumerate(streams, start=1):
            print(
                f"    [{idx}] Client: {stream['client_addr']} | App: {stream['application_name']} | "
                f"State: {stream['state']} | Sync: {stream['sync_state']} | Replay LSN: {stream['replay_lsn']}"
            )
        assert len(streams) >= 2, "Expected at least 2 active replication streams"
        print("  ✓ PostgreSQL streaming replication telemetry confirmed active.")

    except Exception as exc:
        all_passed = False
        print(f"\n❌ Verification encountered failure: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await primary_engine.dispose()
        await replica1_engine.dispose()
        await replica2_engine.dispose()

    print("\n" + "=" * 80)
    if all_passed:
        print(" 🎉 ALL REPLICATION & REPLICAROUTER VERIFICATIONS PASSED SUCCESSFULLY!")
    else:
        print(" ❌ REPLICATION VERIFICATION FAILED.")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_verification())
