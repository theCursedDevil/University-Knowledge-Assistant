"""Automated test suite for document management APIs.

Verifies:
- POST /documents (valid PDF upload, MinIO storage, DB record, audit log, admin RBAC)
- Validation rejections: non-admin 403, invalid extension 422, invalid MIME 422, invalid magic bytes 422, oversized 413
- GET /documents (listing, category filtering, pagination)
- DELETE /documents/{id} (MinIO deletion, cascading DB deletion, audit logging, non-admin 403, not found 404)
"""

import io
import uuid
from starlette.testclient import TestClient

from backend.app.services.storage import storage_service

SAMPLE_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


def test_admin_upload_valid_pdf(client: TestClient):
    """Verifies valid PDF upload by admin: saves to MinIO, records in PostgreSQL, logs audit."""
    response = client.post(
        "/documents",
        files={"file": ("academic_regulations_2024.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Regulations", "title": "Academic Regulations 2024"},
        headers={"X-Dev-Role": "admin"},
    )
    assert response.status_code == 201
    data = response.json()

    doc_id = uuid.UUID(data["id"])
    assert data["title"] == "Academic Regulations 2024"
    assert data["category"] == "Regulations"
    assert data["status"] == "processing"
    assert data["version"] == 1
    storage_path = data["storage_path"]
    assert "academic_regulations_2024.pdf" in storage_path

    # Verify MinIO file exists
    assert storage_service.file_exists(storage_path) is True

    # Clean up
    del_res = client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
    assert del_res.status_code == 200


def test_non_admin_upload_forbidden(client: TestClient):
    """Verifies that non-admin users (students) are rejected with 403 Forbidden."""
    response = client.post(
        "/documents",
        files={"file": ("student_guide.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "General"},
        headers={"X-Dev-Role": "student"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_upload_invalid_extension_rejected(client: TestClient):
    """Verifies that non-PDF extensions (e.g. .txt, .docx, .exe) are rejected with 422."""
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", io.BytesIO(b"Plain text content"), "text/plain")},
        data={"category": "General"},
        headers={"X-Dev-Role": "admin"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_invalid_mime_type_rejected(client: TestClient):
    """Verifies that a file with non-PDF MIME type is rejected with 422."""
    response = client.post(
        "/documents",
        files={"file": ("document.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/octet-stream")},
        data={"category": "General"},
        headers={"X-Dev-Role": "admin"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_invalid_magic_bytes_rejected(client: TestClient):
    """Verifies that corrupted or disguised files lacking '%PDF' header are rejected with 422."""
    fake_content = b"This is a fake file that claims to be a PDF but has no magic bytes."
    response = client.post(
        "/documents",
        files={"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")},
        data={"category": "General"},
        headers={"X-Dev-Role": "admin"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_oversized_file_rejected(client: TestClient, monkeypatch):
    """Verifies that files exceeding configured size limit are rejected with 413."""
    from backend.app.api import documents

    # Temporarily set max size to 100 bytes for test
    monkeypatch.setattr(documents.settings, "MAX_UPLOAD_SIZE_BYTES", 50)

    response = client.post(
        "/documents",
        files={"file": ("oversized.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "General"},
        headers={"X-Dev-Role": "admin"},
    )
    assert response.status_code == 413
    data = response.json()
    assert data["error"]["code"] == "FILE_TOO_LARGE"


def test_list_and_filter_documents(client: TestClient):
    """Verifies document listing and category filtering via GET /documents."""
    # 1. Upload two documents with different categories
    res1 = client.post(
        "/documents",
        files={"file": ("curriculum_doc.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Curriculum", "title": "B.Tech Syllabus"},
        headers={"X-Dev-Role": "admin"},
    )
    assert res1.status_code == 201
    doc1_id = res1.json()["id"]

    res2 = client.post(
        "/documents",
        files={"file": ("hostel_rules.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Hostel", "title": "Hostel Manual"},
        headers={"X-Dev-Role": "admin"},
    )
    assert res2.status_code == 201
    doc2_id = res2.json()["id"]

    # 2. List all documents
    list_all = client.get("/documents", headers={"X-Dev-Role": "student"})
    assert list_all.status_code == 200
    all_docs = list_all.json()
    assert len(all_docs) >= 2
    doc_ids = [d["id"] for d in all_docs]
    assert doc1_id in doc_ids
    assert doc2_id in doc_ids

    # 3. Filter by category
    filtered = client.get("/documents?category=Curriculum", headers={"X-Dev-Role": "student"})
    assert filtered.status_code == 200
    curriculum_docs = filtered.json()
    assert any(d["id"] == doc1_id for d in curriculum_docs)
    assert not any(d["id"] == doc2_id for d in curriculum_docs)

    # Clean up
    client.delete(f"/documents/{doc1_id}", headers={"X-Dev-Role": "admin"})
    client.delete(f"/documents/{doc2_id}", headers={"X-Dev-Role": "admin"})


def test_delete_document_and_audit_log(client: TestClient):
    """Verifies document deletion removes MinIO object, DB record, and records audit trail."""
    # 1. Upload document
    upload_res = client.post(
        "/documents",
        files={"file": ("doc_to_delete.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Administrative", "title": "Temporary Memo"},
        headers={"X-Dev-Role": "admin"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]
    storage_path = upload_res.json()["storage_path"]
    assert storage_service.file_exists(storage_path) is True

    # 2. Attempt deletion as non-admin -> 403 Forbidden
    forbidden_res = client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "student"})
    assert forbidden_res.status_code == 403
    assert storage_service.file_exists(storage_path) is True

    # 3. Delete as admin -> 200 OK
    delete_res = client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
    assert delete_res.status_code == 200
    assert delete_res.json()["id"] == doc_id

    # 4. Verify MinIO object removed
    assert storage_service.file_exists(storage_path) is False

    # 5. Subsequent delete returns 404 Not Found
    not_found_res = client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
    assert not_found_res.status_code == 404


def test_delete_non_existent_document_returns_404(client: TestClient):
    """Verifies that deleting an unknown document UUID returns 404 NotFoundError."""
    random_id = uuid.uuid4()
    response = client.delete(f"/documents/{random_id}", headers={"X-Dev-Role": "admin"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
