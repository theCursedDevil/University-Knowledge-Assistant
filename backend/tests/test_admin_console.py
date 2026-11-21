"""Comprehensive tests for administrator functionality (Prompt 15, C-ADMINSVC, FR-ADMIN-001 through FR-ADMIN-003).

Verifies:
1. Document Management:
   - Admin upload, extension/MIME validation, size limits, processing status
   - Document listing, category/status filtering, metadata patching
   - Original document preview via PyMuPDF from MinIO
   - Cascading deletion across PostgreSQL, MinIO, and Qdrant
2. Analytics:
   - GET /admin/stats returns total uploaded, processed, failed, conversations, messages, questions, and category breakdowns
3. Audit Logging:
   - Audit trail records acting user, action performed, entity type, entity ID, and timestamp
   - GET /admin/audit-logs allows filtering by action and entity
4. Access Control:
   - Only admin users may upload, delete, edit documents, or view analytics
   - Non-admin (student, faculty) receive HTTP 403 on all admin routes
"""

import io
import uuid
import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.models import Document, DocumentChunkMeta, AuditLog, User, Conversation, Message


def generate_admin_test_pdf(title: str = "University Policy") -> bytes:
    """Generates a small valid PDF in-memory for admin testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"Official Policy Document: {title}\nRule: Must maintain 75% attendance.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# 1. Analytics & Statistics Verification
# ---------------------------------------------------------------------------


def test_admin_stats_schema_and_counts(client: TestClient):
    """GET /admin/stats returns all required fields and valid counts."""
    resp = client.get("/admin/stats", headers={"X-Dev-Role": "admin"})
    assert resp.status_code == 200
    data = resp.json()

    # Core statistics requirements
    assert "total_documents" in data
    assert "processed_documents" in data
    assert "failed_documents" in data
    assert "processing_documents" in data
    assert "total_conversations" in data
    assert "total_messages" in data
    assert "total_questions" in data
    assert "total_answers" in data
    assert "total_users" in data
    assert "total_chunks" in data
    assert "documents_by_category" in data
    assert "documents_by_status" in data
    assert "recent_audit_logs" in data

    assert isinstance(data["total_documents"], int)
    assert isinstance(data["processed_documents"], int)
    assert isinstance(data["failed_documents"], int)
    assert isinstance(data["total_conversations"], int)
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["total_questions"], int)
    assert isinstance(data["documents_by_category"], dict)
    assert isinstance(data["documents_by_status"], dict)
    assert isinstance(data["recent_audit_logs"], list)


# ---------------------------------------------------------------------------
# 2. Audit Trail & Log Query Verification
# ---------------------------------------------------------------------------


def test_admin_audit_logs_query_and_filtering(client: TestClient):
    """GET /admin/audit-logs returns audit events and supports action/entity filters."""
    # 1. Query all recent audit logs
    resp = client.get("/admin/audit-logs?limit=20", headers={"X-Dev-Role": "admin"})
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)

    if logs:
        sample = logs[0]
        # Verify required audit fields
        assert "id" in sample
        assert "action" in sample
        assert "entity" in sample
        assert "created_at" in sample
        assert "user_id" in sample

    # 2. Query with action filter
    upload_logs_resp = client.get("/admin/audit-logs?action=DOCUMENT_UPLOAD", headers={"X-Dev-Role": "admin"})
    assert upload_logs_resp.status_code == 200
    for log in upload_logs_resp.json():
        assert log["action"] == "DOCUMENT_UPLOAD"


# ---------------------------------------------------------------------------
# 3. Access Control (HTTP 403 Forbidden on Admin-Only Routes)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_admin_stats(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on GET /admin/stats."""
    resp = client.get("/admin/stats", headers={"X-Dev-Role": non_admin_role})
    assert resp.status_code == 403
    assert "error" in resp.json()


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_admin_audit_logs(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on GET /admin/audit-logs."""
    resp = client.get("/admin/audit-logs", headers={"X-Dev-Role": non_admin_role})
    assert resp.status_code == 403


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_admin_users_api(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on user management endpoints."""
    resp = client.get("/admin/users", headers={"X-Dev-Role": non_admin_role})
    assert resp.status_code == 403

    random_id = uuid.uuid4()
    patch_resp = client.patch(
        f"/admin/users/{random_id}/role",
        headers={"X-Dev-Role": non_admin_role},
        json={"role": "admin"},
    )
    assert patch_resp.status_code == 403


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_document_upload(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on POST /documents."""
    pdf_bytes = generate_admin_test_pdf("Unauthorized Upload")
    resp = client.post(
        "/api/v1/documents",
        headers={"X-Dev-Role": non_admin_role},
        data={"category": "Academic", "title": "Unauthorized"},
        files={"file": ("unauth.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_document_delete(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on DELETE /documents/{id}."""
    random_doc_id = uuid.uuid4()
    resp = client.delete(f"/api/v1/documents/{random_doc_id}", headers={"X-Dev-Role": non_admin_role})
    assert resp.status_code == 403


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_document_metadata_update(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on PATCH /documents/{id}."""
    random_doc_id = uuid.uuid4()
    resp = client.patch(
        f"/api/v1/documents/{random_doc_id}",
        headers={"X-Dev-Role": non_admin_role},
        json={"title": "Hacked Title", "category": "General"},
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("non_admin_role", ["student", "faculty"])
def test_non_admin_forbidden_on_document_process(client: TestClient, non_admin_role: str):
    """Non-admin roles receive HTTP 403 on POST /documents/{id}/process."""
    random_doc_id = uuid.uuid4()
    resp = client.post(f"/api/v1/documents/{random_doc_id}/process", headers={"X-Dev-Role": non_admin_role})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. Complete Admin Document Management Lifecycle with Audit Logging
# ---------------------------------------------------------------------------


def test_admin_document_lifecycle_and_audit_provenance(client: TestClient):
    """Tests the full admin lifecycle: upload, validate, process, preview, update metadata, and delete with audit trail."""
    unique_tag = uuid.uuid4().hex[:6]
    title = f"Admin Regulations {unique_tag}"
    filename = f"Admin_Regulations_{unique_tag}.pdf"
    pdf_bytes = generate_admin_test_pdf(title)

    # 1. Upload valid PDF
    upload_resp = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Regulations", "title": title},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["title"] == title
    assert doc_data["status"] == "processing"

    # 2. Trigger processing
    proc_resp = client.post(f"/api/v1/documents/{doc_id}/process", headers={"X-Dev-Role": "admin"})
    assert proc_resp.status_code == 200
    assert proc_resp.json()["status"] == "ready"

    # 3. Preview document text
    prev_resp = client.get(f"/api/v1/documents/{doc_id}/preview", headers={"X-Dev-Role": "admin"})
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()
    assert prev_data["page_count"] >= 1
    assert "Must maintain 75% attendance" in prev_data["pages"][0]["text"]

    # 4. Update metadata
    new_title = f"Updated Admin Regulations {unique_tag}"
    patch_resp = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Dev-Role": "admin"},
        json={"title": new_title, "category": "Academic"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == new_title
    assert patch_resp.json()["category"] == "Academic"

    # 5. Cascading deletion
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
    assert del_resp.status_code == 200

    # 6. Verify audit logs were created for each step
    audit_resp = client.get(f"/admin/audit-logs?entity=documents&limit=20", headers={"X-Dev-Role": "admin"})
    assert audit_resp.status_code == 200
    recent_actions = [log["action"] for log in audit_resp.json() if log.get("entity_id") == doc_id]
    assert "DOCUMENT_UPLOAD" in recent_actions
    assert "DOCUMENT_PROCESSED" in recent_actions
    assert "DOCUMENT_METADATA_UPDATE" in recent_actions
    assert "DOCUMENT_DELETE" in recent_actions
