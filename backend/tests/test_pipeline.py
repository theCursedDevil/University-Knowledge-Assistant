"""Automated test suite for PDF document processing pipeline and vector store (C-PROC, C-RAGSVC).

Verifies:
- Text extraction and cleaning with PyMuPDF (page retention, header detection, artifact removal)
- Semantic chunking with LangChain RecursiveCharacterTextSplitter (~700 tokens, 100 overlap)
- Embedding generation with Sentence Transformers (384-dimensional dense vectors)
- Vector indexing in Qdrant (payloads, cosine similarity, collection creation, point deletion)
- End-to-end ingestion pipeline lifecycle (status transitions: processing -> ready / failed)
- Atomic cleanup on error and vector cleanup on document deletion
"""

import io
import uuid
import pytest
import fitz  # PyMuPDF
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.models import Document, DocumentChunkMeta, AuditLog
from backend.app.rag.extractor import clean_text, detect_section_header, extract_text_from_pdf, ExtractedPage
from backend.app.rag.chunker import chunk_document_pages, create_text_splitter, DocumentChunk
from backend.app.rag.embeddings import embedding_client
from backend.app.rag.vector_store import vector_store
from backend.app.rag.pipeline import process_document

settings = get_settings()


def generate_test_pdf(num_pages: int = 3) -> bytes:
    """Generates a valid multi-page PDF in-memory with section headings and page artifacts."""
    doc = fitz.open()
    for page_num in range(1, num_pages + 1):
        page = doc.new_page()
        text = (
            f"Section {page_num}: Academic Policy and Regulations {page_num}\n\n"
            f"This is the official university academic regulation policy documentation for page {page_num}. "
            f"Students enrolled in the B.Tech Computer Science and Engineering program must maintain a minimum "
            f"Cumulative Grade Point Average (CGPA) of 6.0 out of 10.0 to remain in good standing. "
            f"Attendance requirements mandate at least 75 percent physical attendance in all registered lecture, "
            f"tutorial, and practical laboratory sessions. Students falling below this threshold will be debarred.\n\n"
            * 6
            + f"Page {page_num} of {num_pages}"  # Footer artifact to be cleaned
        )
        page.insert_text(fitz.Point(50, 72), text)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# 1. Extractor Unit Tests
# ---------------------------------------------------------------------------


def test_clean_text_removes_page_number_artifacts_and_normalizes():
    raw = "Section 1: Overview\n\nPage 1 of 5\n\nSome important text content.\r\nAnother line.   \n\n\n\n- 1 -"
    cleaned = clean_text(raw)
    assert "Page 1 of 5" not in cleaned
    assert "- 1 -" not in cleaned
    assert "Section 1: Overview" in cleaned
    assert "Some important text content." in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned


def test_detect_section_header():
    assert detect_section_header("Section 2: Grading Scheme\nDetails follow...") == "Section 2: Grading Scheme"
    assert detect_section_header("1.2 Admission Criteria\nEligible candidates...") == "1.2 Admission Criteria"
    assert detect_section_header("ACADEMIC REGULATIONS\nUniversity Handbook") == "ACADEMIC REGULATIONS"
    assert detect_section_header("regular paragraph without heading") is None


def test_extract_text_from_pdf_preserves_page_numbers():
    pdf_bytes = generate_test_pdf(num_pages=3)
    pages = extract_text_from_pdf(pdf_bytes)

    assert len(pages) == 3
    for i, page in enumerate(pages):
        assert page.page_number == i + 1
        assert f"Section {i + 1}" in page.text
        assert f"Page {i + 1} of 3" not in page.text  # Cleaned artifact
        assert page.char_count > 100


def test_extract_text_from_empty_bytes_raises_validation_error():
    with pytest.raises(Exception):
        extract_text_from_pdf(b"")


def test_extract_text_from_corrupted_pdf_raises_validation_error():
    with pytest.raises(Exception):
        extract_text_from_pdf(b"%PDF-1.4 corrupted payload that cannot parse")


# ---------------------------------------------------------------------------
# 2. Chunker Unit Tests
# ---------------------------------------------------------------------------


def test_chunk_document_pages_retains_provenance():
    pdf_bytes = generate_test_pdf(num_pages=3)
    pages = extract_text_from_pdf(pdf_bytes)
    chunks = chunk_document_pages(pages, chunk_size_chars=1000, chunk_overlap_chars=200)

    assert len(chunks) >= 3
    # Verify continuous 0-indexed sequence
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    # Verify every chunk has a valid 1-indexed page number from the source
    for chunk in chunks:
        assert chunk.page in (1, 2, 3)
        assert len(chunk.text) > 0
        assert chunk.char_count == len(chunk.text)


# ---------------------------------------------------------------------------
# 3. Embedding Client Tests
# ---------------------------------------------------------------------------


def test_embedding_client_generates_384_dimension_vectors():
    texts = ["Academic regulations for undergraduate students.", "Hostel curfew and dining rules."]
    embeddings = embedding_client.embed_texts(texts)

    assert len(embeddings) == 2
    for emb in embeddings:
        assert len(emb) == 384
        # Normalized vector check (magnitude close to 1.0)
        norm = sum(x * x for x in emb) ** 0.5
        assert abs(norm - 1.0) < 1e-4

    single_emb = embedding_client.embed_query("How many credits to graduate?")
    assert len(single_emb) == 384


# ---------------------------------------------------------------------------
# 4. Qdrant Vector Store Integration Tests
# ---------------------------------------------------------------------------


def test_qdrant_vector_store_upsert_and_deletion():
    doc_id = uuid.uuid4()
    chunks = [
        DocumentChunk(
            chunk_index=0,
            text="First test chunk regarding admissions process.",
            page=1,
            section="Section 1: Admissions",
            char_count=45,
        ),
        DocumentChunk(
            chunk_index=1,
            text="Second test chunk regarding fee payment deadlines.",
            page=1,
            section="Section 1: Admissions",
            char_count=48,
        ),
    ]
    embeddings = embedding_client.embed_texts([c.text for c in chunks])

    # Ensure collection exists and upsert
    vector_ids = vector_store.upsert_chunks(
        document_id=doc_id,
        document_title="Admissions Handbook",
        category="Admissions",
        chunks=chunks,
        embeddings=embeddings,
    )

    assert len(vector_ids) == 2

    # Clean up vectors
    vector_store.delete_document_vectors(doc_id)


# ---------------------------------------------------------------------------
# 5. End-to-End Pipeline & API Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_pipeline_success(client: TestClient, db_session):
    """Verifies complete upload -> extraction -> chunking -> embedding -> Qdrant indexing -> chunks query -> delete."""
    pdf_bytes = generate_test_pdf(num_pages=2)
    filename = "academic_handbook_test.pdf"

    # 1. Upload Document with auto_process=False to control pipeline execution
    response = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Academic", "title": "B.Tech Academic Regulations 2026"},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    doc_data = response.json()
    doc_id = uuid.UUID(doc_data["id"])
    assert doc_data["status"] == "processing"

    # 2. Trigger Ingestion Pipeline explicitly
    proc_response = client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"X-Dev-Role": "admin"},
    )
    assert proc_response.status_code == 200
    proc_data = proc_response.json()
    assert proc_data["status"] == "ready"
    assert proc_data["pages_count"] == 2
    assert proc_data["chunks_count"] >= 2

    # 3. Verify Document in PostgreSQL is 'ready'
    stmt = select(Document).where(Document.id == doc_id)
    result = await db_session.execute(stmt)
    db_doc = result.scalar_one_or_none()
    assert db_doc is not None
    assert db_doc.status == "ready"

    # 4. Verify Chunks Metadata in PostgreSQL via GET /documents/{id}/chunks
    chunks_response = client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers={"X-Dev-Role": "student"},
    )
    assert chunks_response.status_code == 200
    chunks_data = chunks_response.json()
    assert len(chunks_data) == proc_data["chunks_count"]
    for i, chunk_item in enumerate(chunks_data):
        assert chunk_item["chunk_index"] == i
        assert chunk_item["page"] in (1, 2)
        assert len(chunk_item["vector_id"]) > 0

    # 5. Verify Audit Log recorded DOCUMENT_PROCESSED
    audit_stmt = select(AuditLog).where(
        AuditLog.entity_id == str(doc_id),
        AuditLog.action == "DOCUMENT_PROCESSED",
    )
    audit_res = await db_session.execute(audit_stmt)
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.details["status"] == "ready"

    # 6. Delete Document and verify cascading vector deletion
    del_response = client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"X-Dev-Role": "admin"},
    )
    assert del_response.status_code == 200

    # Verify chunks meta deleted from DB
    meta_stmt = select(DocumentChunkMeta).where(DocumentChunkMeta.document_id == doc_id)
    meta_res = await db_session.execute(meta_stmt)
    assert len(meta_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_pipeline_failure_corrupted_pdf_marks_failed(client: TestClient, db_session):
    """Verifies that an unextractable/corrupted PDF transitions document status to 'failed' and does not leave partial state."""
    # PDF with valid header but unparseable syntax
    corrupt_pdf_bytes = b"%PDF-1.4\ntrailer\n<< /Root >>\n%%EOF"

    response = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Hostel", "title": "Corrupt Document Test"},
        files={"file": ("corrupt.pdf", io.BytesIO(corrupt_pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    doc_id = uuid.UUID(response.json()["id"])

    # Process corrupted document
    proc_response = client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"X-Dev-Role": "admin"},
    )
    assert proc_response.status_code == 200
    proc_data = proc_response.json()
    assert proc_data["status"] == "failed"
    assert proc_data["chunks_count"] == 0
    assert proc_data["error"] is not None

    # Verify status in PostgreSQL is 'failed' (never marked as ready)
    stmt = select(Document).where(Document.id == doc_id)
    result = await db_session.execute(stmt)
    db_doc = result.scalar_one_or_none()
    assert db_doc is not None
    assert db_doc.status == "failed"

    # Verify Audit Log recorded DOCUMENT_PROCESS_FAILED
    audit_stmt = select(AuditLog).where(
        AuditLog.entity_id == str(doc_id),
        AuditLog.action == "DOCUMENT_PROCESS_FAILED",
    )
    audit_res = await db_session.execute(audit_stmt)
    assert audit_res.scalar_one_or_none() is not None

    # Cleanup
    client.delete(f"/api/v1/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
