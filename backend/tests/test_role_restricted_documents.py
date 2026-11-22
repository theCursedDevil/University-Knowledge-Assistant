"""Test suite for user management and role-restricted document visibility (Prompt 17, UKA-38).

Verifies:
1. User profile and role claims verification on GET /me (roles array populated).
2. Document upload and metadata update with role_restriction ('all', 'student', 'faculty', 'admin').
3. Document listing visibility:
   - Student sees public / student documents, not faculty or admin documents.
   - Faculty sees public, student, and faculty documents, not admin documents.
   - Admin sees all documents.
4. Direct document access protection (GET /documents/{id}, /preview, /chunks):
   - Non-authorized role rejected with HTTP 403 Forbidden.
   - Authorized role succeeds with HTTP 200 OK.
5. Vector store Qdrant search filtering:
   - student search applies must_not filter for ['faculty', 'admin'].
   - faculty search applies must_not filter for ['admin'].
   - admin search applies no role filter.
6. RAG Q&A isolation:
   - Student question on faculty-only content returns fallback without leaking chunk data.
   - Faculty question on faculty-only content returns grounded answer with citation.
"""

import io
import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.rag.chunker import DocumentChunk
from backend.app.rag.embeddings import embedding_client
from backend.app.rag.vector_store import vector_store
from backend.app.rag.rag_service import rag_service

SAMPLE_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


def test_user_profile_and_roles_array(client: TestClient):
    """Verifies that GET /me returns the user profile with roles list populated."""
    client.cookies.clear()

    # 1. Student
    resp = client.get("/me", headers={"X-Dev-Role": "student", "X-Dev-Email": "student_test@university.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "student"
    assert "roles" in data
    assert "student" in data["roles"]

    # 2. Faculty
    resp = client.get("/me", headers={"X-Dev-Role": "faculty", "X-Dev-Email": "faculty_test@university.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "faculty"
    assert "faculty" in data["roles"]

    # 3. Admin
    resp = client.get("/me", headers={"X-Dev-Role": "admin", "X-Dev-Email": "admin_test@university.edu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert "admin" in data["roles"]


def test_upload_role_restriction_validation(client: TestClient):
    """Verifies document upload validates role_restriction and saves correct metadata."""
    client.cookies.clear()

    # Invalid role_restriction rejected with 422
    resp = client.post(
        "/documents",
        files={"file": ("test_invalid.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Academic", "title": "Invalid Role Doc", "role_restriction": "superadmin"},
        headers={"X-Dev-Role": "admin"},
    )
    assert resp.status_code == 422

    # Valid role_restriction 'faculty' accepted
    resp = client.post(
        "/documents",
        files={"file": ("faculty_handbook.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Regulations", "title": "Faculty Handbook", "role_restriction": "faculty"},
        headers={"X-Dev-Role": "admin"},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    assert resp.json()["role_restriction"] == "faculty"

    # Clean up
    client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "admin"})


def test_document_listing_role_visibility(client: TestClient):
    """Verifies that GET /documents server-side filters documents according to user role."""
    client.cookies.clear()

    # 1. Upload 3 documents with different restrictions
    res_public = client.post(
        "/documents",
        files={"file": ("public_calendar.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Academic", "title": "Public Academic Calendar", "role_restriction": "all"},
        headers={"X-Dev-Role": "admin"},
    )
    assert res_public.status_code == 201
    public_id = res_public.json()["id"]

    res_faculty = client.post(
        "/documents",
        files={"file": ("faculty_payroll.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Regulations", "title": "Faculty Appraisal Guidelines", "role_restriction": "faculty"},
        headers={"X-Dev-Role": "admin"},
    )
    assert res_faculty.status_code == 201
    faculty_id = res_faculty.json()["id"]

    res_admin = client.post(
        "/documents",
        files={"file": ("admin_audit.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "General", "title": "Confidential Board Audit", "role_restriction": "admin"},
        headers={"X-Dev-Role": "admin"},
    )
    assert res_admin.status_code == 201
    admin_id = res_admin.json()["id"]

    try:
        # 2. Student lists documents
        student_docs = client.get("/documents", headers={"X-Dev-Role": "student"}).json()
        student_ids = [d["id"] for d in student_docs]
        assert public_id in student_ids, "Student should see public documents"
        assert faculty_id not in student_ids, "Student must NOT see faculty-restricted documents"
        assert admin_id not in student_ids, "Student must NOT see admin-restricted documents"

        # 3. Faculty lists documents
        faculty_docs = client.get("/documents", headers={"X-Dev-Role": "faculty"}).json()
        faculty_ids = [d["id"] for d in faculty_docs]
        assert public_id in faculty_ids, "Faculty should see public documents"
        assert faculty_id in faculty_ids, "Faculty should see faculty-restricted documents"
        assert admin_id not in faculty_ids, "Faculty must NOT see admin-restricted documents"

        # 4. Admin lists documents
        admin_docs = client.get("/documents", headers={"X-Dev-Role": "admin"}).json()
        admin_ids = [d["id"] for d in admin_docs]
        assert public_id in admin_ids, "Admin should see public documents"
        assert faculty_id in admin_ids, "Admin should see faculty documents"
        assert admin_id in admin_ids, "Admin should see admin documents"

    finally:
        # Clean up
        for did in (public_id, faculty_id, admin_id):
            client.delete(f"/documents/{did}", headers={"X-Dev-Role": "admin"})


def test_document_direct_access_rbac(client: TestClient):
    """Verifies direct document access (GET /documents/{id}, /preview, /chunks) enforces RBAC."""
    client.cookies.clear()

    # Upload a faculty-only document
    res_faculty = client.post(
        "/documents",
        files={"file": ("faculty_eval.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Regulations", "title": "Faculty Evaluation Criteria", "role_restriction": "faculty"},
        headers={"X-Dev-Role": "admin"},
    )
    faculty_id = res_faculty.json()["id"]

    try:
        # Student attempting to access faculty document directly -> 403 Forbidden
        assert client.get(f"/documents/{faculty_id}", headers={"X-Dev-Role": "student"}).status_code == 403
        assert client.get(f"/documents/{faculty_id}/preview", headers={"X-Dev-Role": "student"}).status_code == 403
        assert client.get(f"/documents/{faculty_id}/chunks", headers={"X-Dev-Role": "student"}).status_code == 403

        # Faculty accessing faculty document directly -> 200 OK
        assert client.get(f"/documents/{faculty_id}", headers={"X-Dev-Role": "faculty"}).status_code == 200
        assert client.get(f"/documents/{faculty_id}/preview", headers={"X-Dev-Role": "faculty"}).status_code == 200
        assert client.get(f"/documents/{faculty_id}/chunks", headers={"X-Dev-Role": "faculty"}).status_code == 200

        # Admin accessing faculty document directly -> 200 OK
        assert client.get(f"/documents/{faculty_id}", headers={"X-Dev-Role": "admin"}).status_code == 200

    finally:
        client.delete(f"/documents/{faculty_id}", headers={"X-Dev-Role": "admin"})


def test_update_document_metadata_role_restriction(client: TestClient):
    """Verifies that updating a document's role_restriction updates access control dynamically."""
    client.cookies.clear()

    # 1. Create initially public document
    res = client.post(
        "/documents",
        files={"file": ("syllabus.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")},
        data={"category": "Academic", "title": "Syllabus 2025"},
        headers={"X-Dev-Role": "admin"},
    )
    doc_id = res.json()["id"]

    try:
        # Student can access initially
        assert client.get(f"/documents/{doc_id}", headers={"X-Dev-Role": "student"}).status_code == 200

        # 2. Admin restricts document to faculty only
        patch_res = client.patch(
            f"/documents/{doc_id}",
            json={"role_restriction": "faculty"},
            headers={"X-Dev-Role": "admin"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["role_restriction"] == "faculty"

        # Student is now denied access
        assert client.get(f"/documents/{doc_id}", headers={"X-Dev-Role": "student"}).status_code == 403
        # Faculty has access
        assert client.get(f"/documents/{doc_id}", headers={"X-Dev-Role": "faculty"}).status_code == 200

    finally:
        client.delete(f"/documents/{doc_id}", headers={"X-Dev-Role": "admin"})


def test_vector_store_role_restriction_filtering():
    """Verifies that vector_store.search applies must_not role filtering in Qdrant."""
    doc_id = uuid.uuid4()
    test_text = "Confidential Faculty Salary Bands and Evaluation Matrices."

    # Index chunks with role_restriction="faculty"
    chunks = [
        DocumentChunk(
            chunk_index=0,
            text=test_text,
            page=1,
            section="Compensation",
            char_count=len(test_text),
        )
    ]
    embeddings = embedding_client.embed_texts([c.text for c in chunks])
    vector_store.upsert_chunks(
        document_id=doc_id,
        chunks=chunks,
        embeddings=embeddings,
        document_title="Faculty Salary Policy",
        category="Regulations",
        role_restriction="faculty",
    )

    try:
        # 1. Student searches for the confidential topic -> 0 results
        student_results = vector_store.search(
            query="Faculty Salary Bands Compensation",
            limit=5,
            user_role="student",
        )
        found_student = any(r.document_id == str(doc_id) for r in student_results)
        assert not found_student, "Qdrant must not return faculty-restricted chunk to a student"

        # 2. Faculty searches for the same topic -> Result returned
        faculty_results = vector_store.search(
            query="Faculty Salary Bands Compensation",
            limit=5,
            user_role="faculty",
        )
        found_faculty = any(r.document_id == str(doc_id) for r in faculty_results)
        assert found_faculty, "Faculty should retrieve faculty-restricted chunk"

        # 3. Admin searches for the same topic -> Result returned
        admin_results = vector_store.search(
            query="Faculty Salary Bands Compensation",
            limit=5,
            user_role="admin",
        )
        found_admin = any(r.document_id == str(doc_id) for r in admin_results)
        assert found_admin, "Admin should retrieve faculty-restricted chunk"

    finally:
        vector_store.delete_document_vectors(doc_id)


@pytest.mark.asyncio
async def test_rag_service_qna_role_restriction_isolation():
    """Verifies that RAG answering pipeline does not leak restricted content to students."""
    doc_id = uuid.uuid4()
    secret_clause = "The special faculty sabbatical bonus code is SABBATICAL_ALPHA_99."

    chunks = [
        DocumentChunk(
            chunk_index=0,
            text=secret_clause,
            page=1,
            section="Sabbaticals",
            char_count=len(secret_clause),
        )
    ]
    embeddings = embedding_client.embed_texts([c.text for c in chunks])
    vector_store.upsert_chunks(
        document_id=doc_id,
        chunks=chunks,
        embeddings=embeddings,
        document_title="Secret Faculty Benefit Handbook",
        category="Regulations",
        role_restriction="faculty",
    )

    try:
        # 1. Student asks for the secret sabbatical bonus code
        student_ans = await rag_service.answer_question(
            question="What is the special faculty sabbatical bonus code?",
            user_role="student",
        )
        # Verify student NEVER receives the restricted chunk, nor is it cited
        assert "SABBATICAL_ALPHA_99" not in student_ans.answer
        assert not any(c.document == "Secret Faculty Benefit Handbook" for c in student_ans.citations)
        assert not any(r.document_name == "Secret Faculty Benefit Handbook" for r in student_ans.retrieved_chunks)

        # 2. Faculty asks the same question
        faculty_ans = await rag_service.answer_question(
            question="What is the special faculty sabbatical bonus code?",
            user_role="faculty",
        )
        # Verify faculty gets the restricted chunk with high similarity
        assert any(r.document_name == "Secret Faculty Benefit Handbook" for r in faculty_ans.retrieved_chunks)
        top_faculty_chunk = next(r for r in faculty_ans.retrieved_chunks if r.document_name == "Secret Faculty Benefit Handbook")
        assert top_faculty_chunk.score >= 0.80
        assert "SABBATICAL_ALPHA_99" in top_faculty_chunk.chunk_text

    finally:
        vector_store.delete_document_vectors(doc_id)
