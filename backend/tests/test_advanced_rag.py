"""Unit and Integration Tests for Advanced RAG Improvements (Prompt 26).

Verifies:
1. Feature 1: Hybrid Retrieval (dense vector similarity + metadata filtering + lexical score blending).
2. Feature 2: Modular Candidate Re-ranking (lightweight zero-RAM strategy and candidate selection).
3. Feature 3: Groundedness & Hallucination Verification (factual claim validation against retrieved context).
4. Feature 4: Long Conversation History Summarization (partitioning older turns and context compression).
"""

from backend.app.rag.vector_store import SearchResult
from backend.app.rag.retriever import vector_retriever, compute_lexical_overlap
from backend.app.rag.reranker import chunk_reranker, ChunkReranker
from backend.app.rag.groundedness import groundedness_checker
from backend.app.rag.conversation_summarizer import conversation_summarizer
from backend.app.rag.prompt import build_rag_prompt


# ---------------------------------------------------------------------------
# 1. Feature 1: Hybrid Retrieval Tests
# ---------------------------------------------------------------------------


def test_lexical_overlap_computation():
    """Verifies normalized lexical term overlap calculation."""
    query = "What is the minimum physical attendance percentage for B.Tech?"
    text_match = "Students must maintain at least 75 percent physical attendance in all lectures."
    text_no_match = "Hostel residents must adhere to evening curfew hours."

    score_match = compute_lexical_overlap(query, text_match)
    score_no_match = compute_lexical_overlap(query, text_no_match)

    assert score_match > 0.20, f"Expected positive match score, got {score_match}"
    assert score_no_match == 0.0, f"Expected 0 match score, got {score_no_match}"


def test_retriever_hybrid_mode_blends_scores():
    """Verifies that vector_retriever applies hybrid lexical-vector blending when enabled."""
    res = vector_retriever.retrieve(
        query="What is the CGPA requirement for graduation?",
        top_k=3,
        enable_hybrid=True,
    )
    assert res.is_hybrid is True
    assert isinstance(res.chunks, list)


def test_retriever_category_and_role_metadata_filters():
    """Verifies that category and role filters are passed to vector retrieval without errors."""
    res_academic = vector_retriever.retrieve(
        query="examination rules",
        top_k=2,
        filter_category="Academic",
        user_role="student",
        enable_hybrid=True,
    )
    assert res_academic.is_hybrid is True
    for chunk in res_academic.chunks:
        if chunk.category:
            assert chunk.category == "Academic"


# ---------------------------------------------------------------------------
# 2. Feature 2: Candidate Re-Ranking Tests
# ---------------------------------------------------------------------------


def test_reranker_disabled_by_default_preserves_passthrough():
    """Verifies that re-ranking is disabled by default to preserve local CPU and RAM."""
    candidates = [
        SearchResult(
            chunk_id=f"c-{i}",
            document_id="d-1",
            document_name="Doc 1",
            chunk_text=f"Sample university chunk text content {i}",
            score=0.80 - (i * 0.05),
        )
        for i in range(10)
    ]
    res = chunk_reranker.rerank(query="university regulations", candidates=candidates, top_k=5)
    assert res.strategy_used == "passthrough"
    assert len(res.chunks) == 5
    assert res.chunks[0].chunk_id == "c-0"


def test_reranker_lexical_boost_strategy():
    """Verifies that when enabled, zero-RAM lexical re-ranking boosts chunks with exact query matches."""
    reranker = ChunkReranker(enabled=True)
    c1 = SearchResult(
        chunk_id="c-generic",
        document_id="d-1",
        document_name="Doc 1",
        chunk_text="This general policy describes standard university academic procedures.",
        score=0.85,
    )
    c2 = SearchResult(
        chunk_id="c-targeted",
        document_id="d-1",
        document_name="Doc 1",
        chunk_text="Special Backlog Ordinance: Maximum 3 backlogs permitted for fifth semester registration.",
        score=0.80,
    )

    res = reranker.rerank(
        query="What is the backlog limit for fifth semester?",
        candidates=[c1, c2],
        top_k=2,
        strategy="lexical_boost",
    )
    assert res.strategy_used == "lexical_rrf"
    assert len(res.chunks) == 2
    # The chunk with multiple query keyword hits ("backlog", "fifth", "semester") should be boosted
    assert res.chunks[0].chunk_id == "c-targeted"


# ---------------------------------------------------------------------------
# 3. Feature 3: Groundedness Verification Tests
# ---------------------------------------------------------------------------


def test_groundedness_checker_supported_facts_passes():
    """Verifies that an answer containing factual terms from context is marked grounded."""
    chunks = [
        SearchResult(
            chunk_id="c-1",
            document_id="d-1",
            document_name="Academic Policy",
            chunk_text="Students must maintain a minimum physical attendance of 75% and a CGPA of 6.0.",
            score=0.90,
        )
    ]
    answer = "Based on the policy [Source 1], students must maintain 75% attendance and a CGPA of 6.0."
    report = groundedness_checker.evaluate(answer, chunks, threshold=0.50)

    assert report.is_grounded is True
    assert report.score >= 0.50
    assert report.verified_answer == answer
    assert len(report.unsupported_claims) == 0


def test_groundedness_checker_fallback_honesty():
    """Verifies that insufficient context fallback answers are naturally verified as grounded."""
    chunks = [
        SearchResult(
            chunk_id="c-1",
            document_id="d-1",
            document_name="Hostel Rules",
            chunk_text="Hostel gate closes at 21:30.",
            score=0.40,
        )
    ]
    answer = "I couldn't find sufficient information about this in the available university documents."
    report = groundedness_checker.evaluate(answer, chunks)

    assert report.is_grounded is True
    assert report.score == 1.0
    assert report.verified_answer == answer


def test_groundedness_checker_detects_hallucination_and_provides_safe_correction():
    """Verifies that an answer claiming facts completely absent from context is flagged ungrounded."""
    chunks = [
        SearchResult(
            chunk_id="c-1",
            document_id="d-1",
            document_name="Hostel Rules",
            chunk_text="Hostel gate closes at 21:30 hrs daily.",
            score=0.85,
        )
    ]
    # Fabricated answer with ungrounded claims
    hallucinated_answer = (
        "Students are eligible for a 95% tuition scholarship if they publish in Nature Quantum Physics."
    )
    report = groundedness_checker.evaluate(hallucinated_answer, chunks, threshold=0.50)

    assert report.is_grounded is False
    assert report.score < 0.50
    assert "could not fully verify" in report.verified_answer
    assert len(report.unsupported_claims) > 0


# ---------------------------------------------------------------------------
# 4. Feature 4: Conversation History Summarization Tests
# ---------------------------------------------------------------------------


def test_conversation_summarizer_partitioning():
    """Verifies partitioning into older turns and recent raw turns."""
    turns = [
        {"role": "user", "content": f"Question {i}"}
        for i in range(1, 9)
    ]
    older, recent = conversation_summarizer.partition_history(turns)
    assert len(older) == 4
    assert len(recent) == 4
    assert recent[-1]["content"] == "Question 8"
    assert older[0]["content"] == "Question 1"


def test_conversation_summarizer_generates_summary():
    """Verifies deterministic semantic summary generation from older turns."""
    older = [
        {"role": "user", "content": "What is the minimum attendance required?"},
        {"role": "assistant", "content": "You need 75% attendance for examinations."},
        {"role": "user", "content": "What is the CGPA required?"},
        {"role": "assistant", "content": "You need a CGPA of 6.0 for graduation."},
    ]
    summary = conversation_summarizer.summarize_turns(older)
    assert summary is not None
    assert "Earlier conversation summary" in summary
    assert "attendance" in summary.lower()
    assert "cgpa" in summary.lower()


def test_prompt_construction_with_summary_and_recent_turns():
    """Verifies prompt assembly formats XML summary and recent conversation turns."""
    chunks = [
        SearchResult(
            chunk_id="c-1",
            document_id="d-1",
            document_name="Policy",
            chunk_text="Hostel curfew is 21:30 hrs.",
            score=0.85,
        )
    ]
    history = [
        {"role": "user", "content": "Turn 1: Attendance question?"},
        {"role": "assistant", "content": "Turn 1: 75% attendance."},
        {"role": "user", "content": "Turn 2: CGPA question?"},
        {"role": "assistant", "content": "Turn 2: 6.0 CGPA."},
        {"role": "user", "content": "Turn 3: Hostel curfew question?"},
    ]
    system_prompt, user_prompt = build_rag_prompt(
        question="What time is curfew?",
        chunks=chunks,
        conversation_history=history,
        conversation_summary="Prior context: discussed academic attendance and graduation CGPA.",
        max_recent_turns=2,
    )

    assert "<conversation_summary>" in user_prompt
    assert "Prior context: discussed academic attendance and graduation CGPA." in user_prompt
    assert "</conversation_summary>" in user_prompt
    assert "<conversation_history>" in user_prompt
    assert "Turn 3: Hostel curfew question?" in user_prompt
    assert "</conversation_history>" in user_prompt
    assert "<user_question>\nWhat time is curfew?\n</user_question>" in user_prompt
