#!/usr/bin/env python3
"""PostgreSQL Synchronization Fixes Verification Script (Prompt 20).

Demonstrates and verifies:
1. FEATURE 1: Read-Your-Own-Writes Consistency (FR-DBSYNC-003)
   - User writes data (uploads university circular).
   - Subsequent reads during session window route strictly to Primary.
   - Verifies circular is immediately visible.
   - Reads return to round-robin replica reading after window expiry.
   - Other users' reads are unaffected and continue routing to replicas.

2. FEATURE 2: Optimistic Concurrency Control (FR-DBSYNC-004, FR-DBSYNC-005)
   - Documents track monotonic integer version column.
   - Valid update with matching expected_version increments version.
   - Concurrent/stale update with mismatched expected_version is rejected with HTTP 409 Conflict.
   - Informs caller that document must be refreshed.
"""

import asyncio
import io
import sys
import time
import uuid
from starlette.testclient import TestClient

from backend.app.main import create_app
from backend.app.core.config import get_settings
from backend.app.db.session import replica_router

settings = get_settings()


def run_verification():
    print("=" * 80)
    print(" UNIVERSITY KNOWLEDGE ASSISTANT — SYNCHRONIZATION & CONCURRENCY VERIFICATION")
    print(" Read-Your-Own-Writes Consistency & Optimistic Locking (Prompt 20 / Phase 9)")
    print("=" * 80)

    app = create_app()
    client = TestClient(app)

    all_passed = True

    try:
        # ----------------------------------------------------------------------
        # Feature 1: Read-Your-Own-Writes Demonstration
        # ----------------------------------------------------------------------
        print("\n[Feature 1/2] Demonstrating Read-Your-Own-Writes Consistency (FR-DBSYNC-003)...")
        admin_email = f"sync-admin-{uuid.uuid4().hex[:6]}@university.edu"
        student_email = f"sync-student-{uuid.uuid4().hex[:6]}@university.edu"

        admin_headers = {
            "x-dev-role": "admin",
            "x-dev-email": admin_email,
        }
        student_headers = {
            "x-dev-role": "student",
            "x-dev-email": student_email,
        }

        # Clear write windows to ensure clean initial state
        replica_router.clear_all_write_windows()

        # Initial read before write (should route to replica)
        r0 = client.get("/api/v1/documents", headers=admin_headers)
        r0_route = r0.headers.get("X-Database-Route", "unknown")
        r0_reason = r0.headers.get("X-Database-Route-Reason", "unknown")
        print(f"  1. Initial Document List Read (Admin): Route='{r0_route}' Reason='{r0_reason}'")

        # Step 1: Upload a new university circular
        print("  2. Uploading new university circular: 'Academic_Circular_Spring_2026.pdf'...")
        import fitz
        doc_fitz = fitz.open()
        page = doc_fitz.new_page()
        page.insert_text((50, 72), "University Academic Calendar 2026 Circular\nSemester begins on Jan 10, 2026.")
        pdf_bytes = doc_fitz.tobytes()
        doc_fitz.close()

        files = {
            "file": (
                "Academic_Circular_Spring_2026.pdf",
                io.BytesIO(pdf_bytes),
                "application/pdf",
            )
        }
        data = {
            "title": "Spring 2026 Academic Calendar Circular",
            "category": "Academic",
            "role_restriction": "all",
            "auto_process": "false",
        }

        upload_res = client.post("/api/v1/documents", headers=admin_headers, files=files, data=data)
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        uploaded_doc = upload_res.json()
        doc_id = uploaded_doc["id"]
        initial_version = uploaded_doc["version"]
        print(f"     ✓ Circular uploaded successfully: id={doc_id}, version={initial_version}")

        # Step 2: Immediately reload document list as that user
        print("  3. Immediately reloading document list as uploader (within write window)...")
        r1 = client.get("/api/v1/documents", headers=admin_headers)
        r1_route = r1.headers.get("X-Database-Route")
        r1_reason = r1.headers.get("X-Database-Route-Reason")
        r1_docs = r1.json()
        doc_ids = [d["id"] for d in r1_docs]

        print(f"     • Route: '{r1_route}' | Reason: '{r1_reason}'")
        print(f"     • Uploaded document visible immediately: {doc_id in doc_ids}")

        assert r1_route == "primary", f"Expected primary route during write window, got {r1_route}"
        assert r1_reason == "read-your-own-writes", f"Expected read-your-own-writes reason, got {r1_reason}"
        assert doc_id in doc_ids, "Uploaded document must be visible immediately to the author"
        print("     ✓ Read-your-own-writes consistency confirmed: Routed to Primary.")

        # Step 3: Other user reading concurrently (should route to replica)
        r_other = client.get("/api/v1/documents", headers=student_headers)
        other_route = r_other.headers.get("X-Database-Route")
        other_reason = r_other.headers.get("X-Database-Route-Reason")
        print(f"  4. Other user read (Student): Route='{other_route}' | Reason='{other_reason}'")
        assert "replica" in other_route or other_reason == "round-robin", "Non-writing user should route to replica"
        print("     ✓ Unrelated user correctly balanced to read replica.")

        # Step 4: Wait for session window to expire (or test with short window)
        print("  5. Testing session window expiration and return to replica reading...")
        # Clear admin write window to simulate window expiration
        replica_router.clear_all_write_windows()
        r_expired = client.get("/api/v1/documents", headers=admin_headers)
        exp_route = r_expired.headers.get("X-Database-Route")
        exp_reason = r_expired.headers.get("X-Database-Route-Reason")
        print(f"     • After window expiry: Route='{exp_route}' | Reason='{exp_reason}'")
        assert "replica" in exp_route or exp_reason == "round-robin", "Should return to replica after window expires"
        print("     ✓ Successfully returned to ordinary replica-based reading.")

        # ----------------------------------------------------------------------
        # Feature 2: Optimistic Locking Demonstration
        # ----------------------------------------------------------------------
        print("\n[Feature 2/2] Demonstrating Optimistic Locking & Conflict Resolution (FR-DBSYNC-004/005)...")
        print(f"  1. Target document ID: {doc_id} | Initial version: {initial_version}")

        # Update A: Send expected_version = initial_version (1)
        print("  2. Transaction A: Updating metadata with expected_version = 1...")
        patch_a_res = client.patch(
            f"/api/v1/documents/{doc_id}",
            headers=admin_headers,
            json={
                "title": "Spring 2026 Academic Calendar Circular (Revised by Dept A)",
                "expected_version": initial_version,
            },
        )
        assert patch_a_res.status_code == 200, f"Update A failed: {patch_a_res.text}"
        doc_after_a = patch_a_res.json()
        new_version = doc_after_a["version"]
        print(f"     ✓ Transaction A succeeded: HTTP 200 OK -> New version: {new_version}")
        assert new_version == initial_version + 1, f"Expected version {initial_version + 1}, got {new_version}"

        # Update B: Stale concurrent transaction sends expected_version = 1 (now stale!)
        print("  3. Transaction B: Attempting stale concurrent update with expected_version = 1...")
        patch_b_res = client.patch(
            f"/api/v1/documents/{doc_id}",
            headers=admin_headers,
            json={
                "title": "Spring 2026 Academic Calendar Circular (Conflicting Dept B Edit)",
                "expected_version": initial_version,
            },
        )
        print(f"     • Response status: HTTP {patch_b_res.status_code}")
        assert patch_b_res.status_code == 409, f"Expected 409 Conflict, got {patch_b_res.status_code}: {patch_b_res.text}"
        err_b = patch_b_res.json()["error"]
        print(f"     • Error code: {err_b['code']}")
        print(f"     • Message: {err_b['message']}")
        print(f"     • Details: {err_b.get('details')}")
        assert err_b["code"] == "CONFLICT"
        assert err_b["details"]["expected_version"] == initial_version
        assert err_b["details"]["current_version"] == new_version
        assert err_b["details"]["action_required"] == "refresh_document"
        print("     ✓ Stale transaction B strictly rejected with HTTP 409 Conflict.")

        # Step 4: Refresh document and update with refreshed version
        print("  4. Refreshing document and retrying with latest version...")
        get_fresh = client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers)
        fresh_ver = get_fresh.json()["version"]
        print(f"     • Refreshed version: {fresh_ver}")
        assert fresh_ver == new_version

        patch_retry_res = client.patch(
            f"/api/v1/documents/{doc_id}",
            headers=admin_headers,
            json={
                "title": "Spring 2026 Academic Calendar Circular (Final Approved)",
                "expected_version": fresh_ver,
            },
        )
        assert patch_retry_res.status_code == 200
        final_doc = patch_retry_res.json()
        print(f"     ✓ Retried update succeeded: HTTP 200 OK -> Final version: {final_doc['version']}")
        assert final_doc["version"] == fresh_ver + 1

        # Clean up
        print("  5. Cleaning up test document...")
        del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
        assert del_res.status_code == 200
        print("     ✓ Test document removed cleanly.")

    except Exception as exc:
        all_passed = False
        print(f"\n❌ Verification encountered failure: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    if all_passed:
        print(" 🎉 ALL SYNCHRONIZATION & CONCURRENCY VERIFICATIONS PASSED SUCCESSFULLY!")
    else:
        print(" ❌ SYNCHRONIZATION VERIFICATION FAILED.")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
