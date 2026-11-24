"""Tests for authentication, profile (/me), admin analytics, user management, and metadata editing."""

import io
from starlette.testclient import TestClient

from backend.tests.test_pipeline import generate_test_pdf


def test_get_me_default_admin(client: TestClient):
    """GET /me returns default admin profile."""
    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert "id" in data
    assert "email" in data


def test_get_me_student_role(client: TestClient):
    """GET /me with student role header returns student profile."""
    resp = client.get("/api/v1/me", headers={"X-Dev-Role": "student", "X-Dev-Email": "student.test@university.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "student"
    assert data["email"] == "student.test@university.edu"


def test_auth_login_endpoint(client: TestClient):
    """POST /auth/login provisions user and returns bearer token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "prof.smith@university.edu", "role": "faculty", "name": "Professor Smith"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "prof.smith@university.edu"
    assert data["user"]["role"] == "faculty"
    assert data["token_type"] == "bearer"
    assert "dev-token-faculty" in data["access_token"]


def test_admin_stats_forbidden_for_student(client: TestClient):
    """GET /admin/stats returns 403 Forbidden for student."""
    resp = client.get("/api/v1/admin/stats", headers={"X-Dev-Role": "student"})
    assert resp.status_code == 403


def test_admin_stats_success_for_admin(client: TestClient):
    """GET /admin/stats returns aggregated metrics for admin."""
    resp = client.get("/api/v1/admin/stats", headers={"X-Dev-Role": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "total_chunks" in data
    assert "total_conversations" in data
    assert "total_messages" in data
    assert "total_users" in data
    assert "documents_by_category" in data
    assert "recent_audit_logs" in data


def test_admin_users_list_and_role_update(client: TestClient):
    """GET /admin/users and PATCH /admin/users/{id}/role."""
    # 1. Login a new user to ensure record exists
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "newbie@university.edu", "role": "student", "name": "Newbie Student"},
    )
    user_id = login_resp.json()["user"]["id"]

    # 2. List users
    users_resp = client.get("/api/v1/admin/users", headers={"X-Dev-Role": "admin"})
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert any(u["id"] == user_id for u in users)

    # 3. Update role to faculty
    patch_resp = client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        headers={"X-Dev-Role": "admin"},
        json={"role": "faculty"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "faculty"


def test_admin_self_demotion_rejected(client: TestClient):
    """Admin cannot remove own admin privileges."""
    me_resp = client.get("/api/v1/me", headers={"X-Dev-Role": "admin"})
    admin_id = me_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        headers={"X-Dev-Role": "admin"},
        json={"role": "student"},
    )
    assert patch_resp.status_code == 403


def test_document_get_preview_and_metadata_update(client: TestClient):
    """Test GET /documents/{id}, GET /documents/{id}/preview, and PATCH /documents/{id}."""
    pdf_bytes = generate_test_pdf(num_pages=2)
    filename = "Sample_Handbook.pdf"

    # 1. Upload
    upload_resp = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Handbook", "title": "Sample Handbook"},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 2. GET /documents/{id}
    get_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Sample Handbook"

    # 3. GET /documents/{id}/preview
    preview_resp = client.get(f"/api/v1/documents/{doc_id}/preview")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["page_count"] == 2
    assert len(preview_data["pages"]) == 2

    # 4. PATCH /documents/{id} (Metadata editing - Requirement 16)
    patch_resp = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Dev-Role": "admin"},
        json={"title": "Updated Handbook Title", "category": "Regulations"},
    )
    assert patch_resp.status_code == 200
    updated_doc = patch_resp.json()
    assert updated_doc["title"] == "Updated Handbook Title"
    assert updated_doc["category"] == "Regulations"

    # 5. Non-admin PATCH rejected
    patch_forbidden = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Dev-Role": "student"},
        json={"title": "Hacked Title"},
    )
    assert patch_forbidden.status_code == 403


def test_delete_conversation_endpoint(client: TestClient):
    """Test DELETE /conversations/{id} owner-only deletion."""
    # 1. Create conv as student
    create_resp = client.post(
        "/api/v1/conversations",
        headers={"X-Dev-Role": "student", "X-Dev-Email": "student1@university.edu"},
        json={"title": "Temporary Chat"},
    )
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # 2. Other student cannot delete
    other_del = client.delete(
        f"/api/v1/conversations/{conv_id}",
        headers={"X-Dev-Role": "student", "X-Dev-Email": "other@university.edu"},
    )
    assert other_del.status_code == 403

    # 3. Owner can delete
    owner_del = client.delete(
        f"/api/v1/conversations/{conv_id}",
        headers={"X-Dev-Role": "student", "X-Dev-Email": "student1@university.edu"},
    )
    assert owner_del.status_code == 200
    assert owner_del.json()["id"] == conv_id

    # 4. Verify 404
    get_after = client.get(
        f"/api/v1/conversations/{conv_id}",
        headers={"X-Dev-Role": "student", "X-Dev-Email": "student1@university.edu"},
    )
    assert get_after.status_code == 404
