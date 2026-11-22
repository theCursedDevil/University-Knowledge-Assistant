"""Integration and unit tests for Database Synchronization & Concurrency Control (Phase 9 / Prompt 20).

Validates:
1. Read-Your-Own-Writes Consistency (FR-DBSYNC-003):
   - User write triggers active session window.
   - Subsequent reads during window route strictly to Primary.
   - Uploader immediately sees newly created documents.
   - Other users' reads continue routing to read replicas.
   - Reads return to round-robin replica balancing after window expiration.
2. Optimistic Concurrency Control (FR-DBSYNC-004, FR-DBSYNC-005):
   - Document metadata tracks integer version column.
   - Valid update with matching expected_version increments version monotonically.
   - Stale update with mismatched expected_version returns HTTP 409 Conflict.
   - Error response instructs client that document must be refreshed.
   - Concurrent updates demonstrate race condition resolution.
"""

import io
import time
import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.db.session import replica_router

settings = get_settings()


@pytest.fixture(autouse=True)
def clean_write_windows():
    """Ensures router write windows and replica health are clean before and after each test."""
    replica_router.clear_all_write_windows()
    replica_router.set_replica_health("replica_1", True)
    replica_router.set_replica_health("replica_2", True)
    replica_router.reset_counter()
    yield
    replica_router.clear_all_write_windows()
    replica_router.set_replica_health("replica_1", True)
    replica_router.set_replica_health("replica_2", True)
    replica_router.reset_counter()


def generate_sample_pdf_bytes(title: str = "Test Circular") -> bytes:
    """Generates a valid single-page PDF in memory for upload testing."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\nOfficial university document for sync testing.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_read_your_own_writes_router_logic():
    """Asserts that ReplicaRouter routes reads to Primary within session window and replicas afterwards."""
    test_uid = uuid.uuid4()

    # 1. Before write: router balances across replicas
    target_before = await replica_router.get_read_target(user_id=test_uid)
    assert target_before.name in ("replica_1", "replica_2")
    assert target_before.reason == "round-robin"

    # 2. Record write with 1-second window
    replica_router.record_user_write(test_uid, window_seconds=0.5)
    assert replica_router.is_in_write_window(test_uid) is True

    # 3. Read during write window: strictly routes to Primary
    target_during = await replica_router.get_read_target(user_id=test_uid)
    assert target_during.name == "primary"
    assert target_during.reason == "read-your-own-writes"

    # 4. Wait for window to expire
    time.sleep(0.55)
    assert replica_router.is_in_write_window(test_uid) is False

    # 5. Read after expiration: returns to replica round-robin
    target_after = await replica_router.get_read_target(user_id=test_uid)
    assert target_after.name in ("replica_1", "replica_2")
    assert target_after.reason == "round-robin"


@pytest.mark.asyncio
async def test_other_users_not_affected_by_active_write_window():
    """Asserts that one user's write window does not redirect other users to Primary."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    replica_router.record_user_write(user_a, window_seconds=5.0)

    # User A routes to Primary
    target_a = await replica_router.get_read_target(user_id=user_a)
    assert target_a.name == "primary"
    assert target_a.reason == "read-your-own-writes"

    # User B is unaffected and routes to replica
    target_b = await replica_router.get_read_target(user_id=user_b)
    assert target_b.name in ("replica_1", "replica_2")
    assert target_b.reason == "round-robin"


def test_document_upload_workflow_read_your_own_writes(client: TestClient):
    """Demonstrates document upload workflow with immediate visibility and primary routing header."""
    admin_email = f"uploader-{uuid.uuid4().hex[:6]}@test.edu"
    headers = {"x-dev-role": "admin", "x-dev-email": admin_email}

    # Step 1: Upload a circular
    pdf_bytes = generate_sample_pdf_bytes("Academic Circular 2026")
    files = {"file": ("circular.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "title": "Academic Calendar Circular 2026",
        "category": "Academic",
        "role_restriction": "all",
        "auto_process": "false",
    }
    upload_res = client.post("/api/v1/documents", headers=headers, files=files, data=data)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Step 2: Immediately reload document list
    list_res = client.get("/api/v1/documents", headers=headers)
    assert list_res.status_code == 200
    assert list_res.headers.get("X-Database-Route") == "primary"
    assert list_res.headers.get("X-Database-Route-Reason") == "read-your-own-writes"

    # Verify newly created document is immediately visible
    doc_ids = [d["id"] for d in list_res.json()]
    assert doc_id in doc_ids

    # Step 3: Cleanup
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200


def test_optimistic_locking_metadata_update_increments_version(client: TestClient):
    """Verifies that updating document metadata with expected_version increments version from 1 to 2."""
    headers = {"x-dev-role": "admin", "x-dev-email": f"opt-admin-{uuid.uuid4().hex[:6]}@test.edu"}

    # Upload doc (version 1)
    pdf_bytes = generate_sample_pdf_bytes("Opt Lock Test")
    files = {"file": ("opt_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Initial Title", "category": "Administrative", "auto_process": "false"}
    upload_res = client.post("/api/v1/documents", headers=headers, files=files, data=data)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["version"] == 1

    # Update with expected_version = 1
    patch_res = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers,
        json={"title": "Updated Title Version 2", "expected_version": 1},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["title"] == "Updated Title Version 2"
    assert updated_data["version"] == 2

    # Cleanup
    client.delete(f"/api/v1/documents/{doc_id}", headers=headers)


def test_optimistic_locking_stale_update_returns_409_conflict(client: TestClient):
    """Verifies that updating document with a stale expected_version returns HTTP 409 Conflict."""
    headers = {"x-dev-role": "admin", "x-dev-email": f"conflict-{uuid.uuid4().hex[:6]}@test.edu"}

    # Upload doc (version 1)
    pdf_bytes = generate_sample_pdf_bytes("Conflict Doc")
    files = {"file": ("conflict.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Base Title", "category": "Administrative", "auto_process": "false"}
    doc_id = client.post("/api/v1/documents", headers=headers, files=files, data=data).json()["id"]

    # First update: version 1 -> 2
    r1 = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers,
        json={"title": "First Update Title", "expected_version": 1},
    )
    assert r1.status_code == 200
    assert r1.json()["version"] == 2

    # Stale second update: sends expected_version = 1 (current is 2)
    r2 = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers,
        json={"title": "Stale Update Title", "expected_version": 1},
    )
    assert r2.status_code == 409
    error_payload = r2.json()["error"]
    assert error_payload["code"] == "CONFLICT"
    assert "Expected version 1" in error_payload["message"]
    assert error_payload["details"]["expected_version"] == 1
    assert error_payload["details"]["current_version"] == 2
    assert error_payload["details"]["action_required"] == "refresh_document"

    # Cleanup
    client.delete(f"/api/v1/documents/{doc_id}", headers=headers)


def test_concurrent_metadata_updates_demonstration(client: TestClient):
    """Demonstrates two concurrent edits from version 1: first succeeds, second is rejected."""
    headers_a = {"x-dev-role": "admin", "x-dev-email": "admin-dept-a@test.edu"}
    headers_b = {"x-dev-role": "admin", "x-dev-email": "admin-dept-b@test.edu"}

    # Initial document version 1
    pdf_bytes = generate_sample_pdf_bytes("Concurrent Notice")
    files = {"file": ("concurrent.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Original Circular", "category": "Academic", "auto_process": "false"}
    doc_id = client.post("/api/v1/documents", headers=headers_a, files=files, data=data).json()["id"]

    # Both dept A and dept B read the document at version 1
    doc_v1 = client.get(f"/api/v1/documents/{doc_id}", headers=headers_a).json()
    assert doc_v1["version"] == 1

    # Dept A submits update first
    res_a = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers_a,
        json={"title": "Dept A Approved Circular", "expected_version": doc_v1["version"]},
    )
    assert res_a.status_code == 200
    assert res_a.json()["version"] == 2

    # Dept B submits update based on stale version 1
    res_b = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers_b,
        json={"title": "Dept B Competing Circular", "expected_version": doc_v1["version"]},
    )
    assert res_b.status_code == 409
    assert res_b.json()["error"]["code"] == "CONFLICT"

    # Dept B refreshes and retries with version 2
    doc_refreshed = client.get(f"/api/v1/documents/{doc_id}", headers=headers_b).json()
    assert doc_refreshed["version"] == 2

    res_b_retry = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=headers_b,
        json={"title": "Dept B Resolved Circular", "expected_version": doc_refreshed["version"]},
    )
    assert res_b_retry.status_code == 200
    assert res_b_retry.json()["version"] == 3

    # Cleanup
    client.delete(f"/api/v1/documents/{doc_id}", headers=headers_a)
