"""Automated test suite for Redis caching and distributed locking (C-CACHE, FR-CACHE-001, FR-CACHE-002, FR-CACHE-003).

Covers:
1. Cache hit & miss logic (X-Cache header).
2. Cache expiration policy (TTL).
3. Cache invalidation on document writes (upload, update, delete, processing).
4. Admin stats caching and invalidation.
5. Distributed lock acquisition, timeout, and reliable release.
6. Safe lock release protection via atomic Lua script.
7. Lock contention on concurrent document processing and deletion.
"""

import io
import time
import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.main import create_app
from backend.app.core.config import get_settings
from backend.app.core.cache import cache_client, DistributedLock, distributed_lock, async_distributed_lock
from backend.app.core.errors import LockContentionError
from backend.app.db.session import replica_router

settings = get_settings()


@pytest.fixture(autouse=True)
def clean_cache_and_write_windows():
    """Flushes application cache and reset write windows before and after each test."""
    cache_client.clear_all()
    replica_router.clear_all_write_windows()
    yield
    cache_client.clear_all()
    replica_router.clear_all_write_windows()


@pytest.fixture
def admin_token_headers():
    """Administrator role authorization headers for dev testing."""
    return {"X-Dev-Role": "admin", "X-Dev-Email": "admin@university.edu"}


@pytest.fixture
def student_token_headers():
    """Student role authorization headers for dev testing."""
    return {"X-Dev-Role": "student", "X-Dev-Email": "student@university.edu"}


# ==============================================================================
# Feature 1: Caching Tests (FR-CACHE-001, FR-CACHE-003)
# ==============================================================================


def test_cache_client_basic_crud():
    """Verifies low-level cache set, get, miss, and delete operations."""
    key = "cache:test:item_1"

    # 1. Miss on non-existent key
    assert cache_client.get(key) is None

    # 2. Set with TTL
    payload = {"name": "B.Tech Handbook", "version": 1, "status": "ready"}
    assert cache_client.set(key, payload, ttl=10) is True

    # 3. Hit
    cached = cache_client.get(key)
    assert cached == payload

    # 4. Delete
    assert cache_client.delete(key) is True
    assert cache_client.get(key) is None


def test_cache_expiration():
    """Verifies that cached entries expire after their configured TTL (FR-CACHE-003)."""
    key = "cache:test:expiring_item"
    assert cache_client.set(key, "short_lived_value", ttl=1) is True

    # Immediate hit
    assert cache_client.get(key) == "short_lived_value"

    # Wait for TTL expiration
    time.sleep(1.2)

    # Miss after expiration
    assert cache_client.get(key) is None


def test_cache_prefix_invalidation():
    """Verifies that invalidate_prefix clears all matching role and filter keys."""
    keys = [
        "cache:documents:list:student:all:0:100",
        "cache:documents:list:faculty:all:0:100",
        "cache:documents:list:admin:Academic:0:50",
        "cache:documents:detail:doc-uuid-1",
        "cache:admin:stats",
    ]
    for k in keys:
        cache_client.set(k, {"key": k}, ttl=60)
        assert cache_client.get(k) is not None

    # Invalidate all document listing variations and doc details
    cache_client.invalidate_document_caches(document_id="doc-uuid-1")

    for k in keys:
        assert cache_client.get(k) is None, f"Expected key '{k}' to be invalidated"


def test_documents_endpoint_cache_hit_and_miss(client: TestClient, admin_token_headers: dict):
    """Verifies read-through caching and X-Cache header behavior on GET /documents."""
    # First request: Cache MISS (queries database and populates Redis)
    res1 = client.get("/documents", headers=admin_token_headers)
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"
    data1 = res1.json()

    # Second request: Cache HIT (served from Redis)
    res2 = client.get("/documents", headers=admin_token_headers)
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"
    data2 = res2.json()

    assert data1 == data2


def test_admin_stats_cache_hit_and_miss(client: TestClient, admin_token_headers: dict):
    """Verifies caching and X-Cache header on GET /admin/stats."""
    res1 = client.get("/admin/stats", headers=admin_token_headers)
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"

    res2 = client.get("/admin/stats", headers=admin_token_headers)
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"
    assert res1.json() == res2.json()


def test_cache_invalidation_after_document_upload(client: TestClient, admin_token_headers: dict):
    """Verifies that uploading a document purges the cached document list and admin stats."""
    # 1. Warm cache
    res_warm = client.get("/documents", headers=admin_token_headers)
    assert res_warm.status_code == 200
    assert client.get("/documents", headers=admin_token_headers).headers.get("X-Cache") == "HIT"
    assert client.get("/admin/stats", headers=admin_token_headers).headers.get("X-Cache") == "MISS"
    assert client.get("/admin/stats", headers=admin_token_headers).headers.get("X-Cache") == "HIT"

    # 2. Upload document
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/documents",
        data={"title": "Cache Invalidation Test Doc", "category": "Academic", "role_restriction": "all"},
        files={"file": ("cache_test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        params={"auto_process": False},
        headers=admin_token_headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 3. Verify that GET /documents is now a Cache MISS and reflects new document
    res_after = client.get("/documents", headers=admin_token_headers)
    assert res_after.status_code == 200
    assert res_after.headers.get("X-Cache") == "MISS"
    doc_ids = [d["id"] for d in res_after.json()]
    assert doc_id in doc_ids

    # 4. Verify admin stats cache is also invalidated
    res_stats_after = client.get("/admin/stats", headers=admin_token_headers)
    assert res_stats_after.status_code == 200
    assert res_stats_after.headers.get("X-Cache") == "MISS"

    # Clean up created document
    client.delete(f"/documents/{doc_id}", headers=admin_token_headers)


def test_cache_invalidation_after_metadata_update(client: TestClient, admin_token_headers: dict):
    """Verifies that updating document metadata invalidates both document list and detail caches."""
    # 1. Upload initial document
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/documents",
        data={"title": "Pre-Update Title", "category": "Regulations", "role_restriction": "all"},
        files={"file": ("pre_update.pdf", io.BytesIO(pdf_content), "application/pdf")},
        params={"auto_process": False},
        headers=admin_token_headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Warm detail and list caches
    client.get(f"/documents/{doc_id}", headers=admin_token_headers)
    assert client.get(f"/documents/{doc_id}", headers=admin_token_headers).headers.get("X-Cache") == "HIT"
    client.get("/documents", headers=admin_token_headers)
    assert client.get("/documents", headers=admin_token_headers).headers.get("X-Cache") == "HIT"

    # 3. Patch metadata
    patch_res = client.patch(
        f"/documents/{doc_id}",
        json={"title": "Post-Update Title", "expected_version": 1},
        headers=admin_token_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Post-Update Title"

    # 4. Verify detail and list caches were invalidated
    res_detail = client.get(f"/documents/{doc_id}", headers=admin_token_headers)
    assert res_detail.headers.get("X-Cache") == "MISS"
    assert res_detail.json()["title"] == "Post-Update Title"

    res_list = client.get("/documents", headers=admin_token_headers)
    assert res_list.headers.get("X-Cache") == "MISS"

    # Clean up
    client.delete(f"/documents/{doc_id}", headers=admin_token_headers)


# ==============================================================================
# Feature 2: Distributed Locking Tests (FR-CACHE-002)
# ==============================================================================


def test_distributed_lock_acquisition_and_release():
    """Verifies normal lock acquisition, state verification, and safe release."""
    resource = f"test:unit:{uuid.uuid4()}"
    lock = DistributedLock(resource, expire_seconds=10.0, timeout_seconds=1.0)

    assert not lock.is_locked()

    # 1. Acquire
    assert lock.acquire() is True
    assert lock.is_locked()
    assert lock.token is not None

    # 2. Release
    assert lock.release() is True
    assert not lock.is_locked()
    assert lock.token is None


def test_distributed_lock_context_managers():
    """Verifies sync and async context managers handle acquisition and release automatically."""
    resource = f"test:ctx:{uuid.uuid4()}"
    checker = DistributedLock(resource)

    # Synchronous context manager
    with distributed_lock(resource, expire_seconds=10.0):
        assert checker.is_locked()

    assert not checker.is_locked()


@pytest.mark.asyncio
async def test_async_distributed_lock_context_manager():
    """Verifies async distributed lock context manager."""
    resource = f"test:async_ctx:{uuid.uuid4()}"
    checker = DistributedLock(resource)

    async with async_distributed_lock(resource, expire_seconds=10.0):
        assert checker.is_locked()

    assert not checker.is_locked()


def test_distributed_lock_contention_and_timeout():
    """Verifies that a second client cannot acquire a held lock and raises LockContentionError."""
    resource = f"test:contention:{uuid.uuid4()}"

    lock1 = DistributedLock(resource, expire_seconds=10.0, timeout_seconds=1.0)
    lock2 = DistributedLock(resource, expire_seconds=10.0, timeout_seconds=0.1)

    # Client 1 acquires lock
    assert lock1.acquire() is True

    # Client 2 attempts acquisition with low timeout -> should raise LockContentionError
    with pytest.raises(LockContentionError) as exc_info:
        lock2.acquire(timeout=0.1)

    assert exc_info.value.code == "LOCK_CONTENTION"
    assert exc_info.value.status_code == 409

    # Client 1 releases
    assert lock1.release() is True

    # Client 2 now succeeds
    assert lock2.acquire(timeout=0.5) is True
    assert lock2.release() is True


def test_lua_script_prevents_releasing_other_clients_lock():
    """Verifies that a client whose lock expired cannot inadvertently delete a subsequent holder's lock."""
    resource = f"test:lua_safety:{uuid.uuid4()}"
    client_a = DistributedLock(resource, expire_seconds=10.0)
    client_b = DistributedLock(resource, expire_seconds=10.0)

    # 1. Client A acquires lock
    assert client_a.acquire() is True
    token_a = client_a.token

    # 2. Simulate Client A's lock expiring and Client B acquiring it
    # We overwrite the Redis key with Client B's token directly
    manager = client_a._manager
    redis_raw = manager.get_client()
    if redis_raw:
        # Overwrite with token B
        token_b = str(uuid.uuid4())
        redis_raw.set(client_a.lock_key, token_b)

        # Client A attempts to release (believing it still holds the lock)
        # Lua script must check if value == token_a and reject release (return 0)
        released = client_a.release()
        assert released is False

        # Key should STILL exist in Redis holding token_b!
        assert redis_raw.get(client_a.lock_key) == token_b

        # Clean up
        redis_raw.delete(client_a.lock_key)
    else:
        client_a.release()


def test_concurrent_processing_lock_rejection(client: TestClient, admin_token_headers: dict):
    """Verifies that triggering processing while a lock is held returns HTTP 409 Conflict."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/documents",
        data={"title": "Lock Contention Doc", "category": "Academic", "role_restriction": "all"},
        files={"file": ("lock_contention.pdf", io.BytesIO(pdf_content), "application/pdf")},
        params={"auto_process": False},
        headers=admin_token_headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]
    lock_key = f"document:{doc_id}"

    # Simulate an active background pipeline holding the lock
    with distributed_lock(lock_key, expire_seconds=15.0):
        # Admin attempts to trigger processing concurrently
        res = client.post(
            f"/documents/{doc_id}/process",
            headers=admin_token_headers,
        )
        assert res.status_code == 409
        err = res.json()["error"]
        assert err["code"] == "LOCK_CONTENTION"
        assert f"'{lock_key}'" in err["message"] or f"'{doc_id}'" in err["message"]

    # Clean up
    client.delete(f"/documents/{doc_id}", headers=admin_token_headers)


def test_document_deletion_blocked_by_active_lock(client: TestClient, admin_token_headers: dict):
    """Verifies that attempting to delete a document while its lock is held is rejected with 409."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/documents",
        data={"title": "Lock Deletion Doc", "category": "Academic", "role_restriction": "all"},
        files={"file": ("lock_delete.pdf", io.BytesIO(pdf_content), "application/pdf")},
        params={"auto_process": False},
        headers=admin_token_headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]
    lock_key = f"document:{doc_id}"

    with distributed_lock(lock_key, expire_seconds=15.0):
        # Admin attempts to delete while ingestion/processing is holding the lock
        res = client.delete(
            f"/documents/{doc_id}",
            headers=admin_token_headers,
        )
        assert res.status_code == 409
        err = res.json()["error"]
        assert err["code"] == "LOCK_CONTENTION"

    # Clean up after lock is released
    del_res = client.delete(f"/documents/{doc_id}", headers=admin_token_headers)
    assert del_res.status_code == 200
