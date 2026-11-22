"""Independent unit and integration tests for deterministic citation resolution (C-CIT, FR-CIT-001 through FR-CIT-007).

Verifies:
- Chunk IDs map strictly to PostgreSQL document_chunks_meta and documents
- Filename and 1-indexed page numbers are populated from verified records
- Section information is included only when actually extracted
- Duplicate citations for the same source/page are deduplicated
- Incomplete metadata (missing filename or page) causes the citation to be safely omitted
- Zero fabricated citations: every citation traces back to an actual retrieved chunk
- Output JSON format strictly matches {"answer": "...", "citations": [{"document": "...", "page": 1, "section": "..."}]}
"""

import io
import uuid
import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.models import DocumentChunkMeta
from backend.app.rag.vector_store import SearchResult
from backend.app.rag.citation import citation_resolver
from backend.tests.test_pipeline import generate_test_pdf


# ---------------------------------------------------------------------------
# 1. Independent Unit Tests for CitationResolver Logic
# ---------------------------------------------------------------------------


def test_build_citation_with_complete_metadata():
    """Verifies that complete metadata properly builds a Citation instance."""
    cit = citation_resolver._build_citation(
        document_storage_path="university-documents/documents/uuid/Examination_Regulations.pdf",
        document_title="Examination Regulations 2026",
        page=12,
        section="Re-evaluation",
    )
    assert cit is not None
    assert cit.document == "Examination_Regulations.pdf"
    assert cit.page == 12
    assert cit.section == "Re-evaluation"


def test_build_citation_omits_section_when_not_extracted():
    """Requirement 6: Include section information only when actually extracted."""
    cit = citation_resolver._build_citation(
        document_storage_path="university-documents/documents/uuid/Hostel_Manual.pdf",
        document_title="Hostel Manual",
        page=5,
        section=None,
    )
    assert cit is not None
    assert cit.document == "Hostel_Manual.pdf"
    assert cit.page == 5
    assert cit.section is None


def test_build_citation_omits_incomplete_metadata():
    """Requirement 9: If metadata is incomplete (missing page or missing document), omit the citation."""
    # Missing page
    cit1 = citation_resolver._build_citation(
        document_storage_path="documents/test.pdf",
        document_title="Test Document",
        page=None,
        section="Intro",
    )
    assert cit1 is None

    # Invalid page <= 0
    cit2 = citation_resolver._build_citation(
        document_storage_path="documents/test.pdf",
        document_title="Test Document",
        page=0,
        section="Intro",
    )
    assert cit2 is None

    # Missing filename and missing title
    cit3 = citation_resolver._build_citation(
        document_storage_path=None,
        document_title="",
        page=3,
        section="Intro",
    )
    assert cit3 is None


def test_deduplication_for_same_source_and_page():
    """Requirement 7: Avoid duplicate citations for the same source/page."""
    chunks = [
        SearchResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            document_name="Academic_Calendar.pdf",
            chunk_text="Fall semester starts on August 10th.",
            page=2,
            section="Fall Term",
            score=0.88,
        ),
        SearchResult(
            chunk_id="chunk-2",
            document_id="doc-1",
            document_name="Academic_Calendar.pdf",
            chunk_text="Course registration deadline is August 15th.",
            page=2,  # Same document, same page 2
            section="Fall Term",
            score=0.84,
        ),
        SearchResult(
            chunk_id="chunk-3",
            document_id="doc-1",
            document_name="Academic_Calendar.pdf",
            chunk_text="Spring semester fee payment is January 5th.",
            page=4,  # Same document, different page 4
            section="Spring Term",
            score=0.79,
        ),
    ]

    citations = citation_resolver.resolve_from_search_results(chunks)
    assert len(citations) == 2  # Deduplicated from 3 to 2
    assert citations[0].document == "Academic_Calendar.pdf"
    assert citations[0].page == 2
    assert citations[1].document == "Academic_Calendar.pdf"
    assert citations[1].page == 4


# ---------------------------------------------------------------------------
# 2. Database Mapping Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_from_chunk_ids_against_live_database(client: TestClient, db_session):
    """Requirements 1, 2, 3: Maps chunk IDs to PostgreSQL document_chunks_meta,
    retrieves associated document record, and builds strictly verified citations."""
    pdf_bytes = generate_test_pdf(num_pages=3)
    filename = "Examination_Regulations.pdf"

    # 1. Upload & index document
    upload_resp = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Academic", "title": "University Examination Regulations"},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = uuid.UUID(upload_resp.json()["id"])

    proc_resp = client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"X-Dev-Role": "admin"},
    )
    assert proc_resp.status_code == 200

    # 2. Fetch chunk metadata from PostgreSQL to obtain real vector IDs
    stmt = (
        select(DocumentChunkMeta)
        .where(DocumentChunkMeta.document_id == doc_id)
        .order_by(DocumentChunkMeta.chunk_index.asc())
    )
    result = await db_session.execute(stmt)
    chunks_meta = result.scalars().all()
    assert len(chunks_meta) >= 2

    chunk_ids = [c.vector_id for c in chunks_meta]

    # 3. Test citation resolver independently against DB
    citations = await citation_resolver.resolve_from_chunk_ids(chunk_ids, session=db_session)
    assert len(citations) >= 2

    # Verify each citation traces back to a verified database chunk
    for cit in citations:
        assert cit.document == filename
        assert cit.page in [1, 2, 3]
        # Verify page matches one of the chunks
        matching_meta = [c for c in chunks_meta if c.page == cit.page]
        assert len(matching_meta) > 0

    # Clean up
    client.delete(f"/api/v1/documents/{doc_id}", headers={"X-Dev-Role": "admin"})


# ---------------------------------------------------------------------------
# 3. End-to-End RAG Citations Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_to_end_rag_citations_structure(client: TestClient, db_session):
    """Verifies that RAG answers return structured citation information with document, page, and section."""
    unique_code = uuid.uuid4().hex[:8]
    filename = f"Examination_Regulations_{unique_code}.pdf"
    doc = fitz.open()
    page = doc.new_page()
    text = (
        f"Section 1: Re-evaluation Policy {unique_code}\n\n"
        f"Under regulation {unique_code}, examination re-evaluation requests must be submitted within 14 calendar days.\n"
    )
    page.insert_textbox(fitz.Rect(50, 50, 550, 780), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    # 1. Upload & process
    upload_resp = client.post(
        "/api/v1/documents?auto_process=false",
        headers={"X-Dev-Role": "admin"},
        data={"category": "Examination", "title": f"Examination Regulations {unique_code}"},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = uuid.UUID(upload_resp.json()["id"])

    proc_resp = client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"X-Dev-Role": "admin"},
    )
    assert proc_resp.status_code == 200

    # 2. Query RAG API endpoint
    response = client.post(
        "/api/v1/rag/query",
        headers={"X-Dev-Role": "student"},
        json={
            "question": f"Within how many days must re-evaluation requests be submitted under {unique_code}?",
            "top_k": 3,
            "confidence_threshold": 0.20,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches example: {"answer": "...", "citations": [{"document": "...", "page": 1, "section": "..."}]}
    assert "answer" in data
    assert "citations" in data
    assert len(data["answer"]) > 10
    assert len(data["citations"]) > 0

    # Verify that the newly indexed document is cited and metadata is valid
    assert any(cit["document"] == filename for cit in data["citations"])
    for cit in data["citations"]:
        assert "document" in cit
        assert "page" in cit
        assert isinstance(cit["page"], int)
        assert cit["page"] >= 1

    # 3. Clean up
    client.delete(f"/api/v1/documents/{doc_id}", headers={"X-Dev-Role": "admin"})
