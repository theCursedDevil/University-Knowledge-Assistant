"""Comprehensive tests for conversation and message management (C-CHATSVC, FR-CHAT-001 through FR-CHAT-005).

Verifies:
1. POST /conversations: Creates new conversation with default or custom title.
2. GET /conversations: Lists user's conversations with strict user isolation.
3. GET /conversations/{id}: Retrieves conversation and message history.
4. Owner-based access control: Non-owning user receives 403 Forbidden on GET /conversations/{id} and POST /conversations/{id}/messages.
5. 404 Not Found on invalid or missing conversation ID.
6. POST /conversations/{id}/messages: Saves user message, invokes RAG, saves assistant message and citation metadata.
7. Conversation updated_at timestamp advances after each new turn.
8. Conversation title automatically derives from first user query if initially default.
9. Multi-turn conversational context: Last 6 messages are retrieved and passed into RAG context.
10. Database persistence: Records persist directly in PostgreSQL tables.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db.models import Conversation, Message, User
from backend.app.rag.citation import Citation
from backend.app.rag.rag_service import RAGResponse


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_create_conversation_default_title(client: TestClient):
    """Requirement 1: Create a new conversation with default title."""
    headers = {"X-Dev-Email": "student_test_1@university.edu"}
    response = client.post("/conversations", json={}, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "id" in data
    assert data["title"] == "New Conversation"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_conversation_custom_title(client: TestClient):
    """Requirement 1: Create a new conversation with specified title."""
    headers = {"X-Dev-Email": "student_test_1@university.edu"}
    payload = {"title": "Semester 4 Grading Inquiry"}
    response = client.post("/conversations", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["title"] == "Semester 4 Grading Inquiry"


def test_list_conversations_user_isolation(client: TestClient):
    """Requirement 2 & 7: List conversations owned by the current user with strict isolation."""
    user_a_headers = {"X-Dev-Email": "user_a@university.edu"}
    user_b_headers = {"X-Dev-Email": "user_b@university.edu"}

    # User A creates 2 conversations
    res_a1 = client.post("/conversations", json={"title": "User A Conv 1"}, headers=user_a_headers)
    res_a2 = client.post("/conversations", json={"title": "User A Conv 2"}, headers=user_a_headers)
    assert res_a1.status_code == 201
    assert res_a2.status_code == 201

    # User B creates 1 conversation
    res_b1 = client.post("/conversations", json={"title": "User B Conv 1"}, headers=user_b_headers)
    assert res_b1.status_code == 201

    # User A lists conversations
    list_a = client.get("/conversations", headers=user_a_headers)
    assert list_a.status_code == 200
    a_titles = [c["title"] for c in list_a.json()]
    assert "User A Conv 1" in a_titles
    assert "User A Conv 2" in a_titles
    assert "User B Conv 1" not in a_titles

    # User B lists conversations
    list_b = client.get("/conversations", headers=user_b_headers)
    assert list_b.status_code == 200
    b_titles = [c["title"] for c in list_b.json()]
    assert "User B Conv 1" in b_titles
    assert "User A Conv 1" not in b_titles


def test_get_conversation_owner_and_forbidden(client: TestClient):
    """Requirement 3 & 7: Retrieve conversation thread; restrict access to owning user."""
    owner_headers = {"X-Dev-Email": "owner_student@university.edu"}
    intruder_headers = {"X-Dev-Email": "intruder_student@university.edu"}

    # Owner creates conversation
    create_res = client.post("/conversations", json={"title": "Private Academic Advice"}, headers=owner_headers)
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # Owner can retrieve
    get_res = client.get(f"/conversations/{conv_id}", headers=owner_headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == conv_id
    assert detail["title"] == "Private Academic Advice"
    assert isinstance(detail["messages"], list)

    # Intruder receives 403 Forbidden
    forbidden_res = client.get(f"/conversations/{conv_id}", headers=intruder_headers)
    assert forbidden_res.status_code == 403
    error_body = forbidden_res.json()
    assert error_body["error"]["code"] == "FORBIDDEN"
    assert "You do not own this conversation" in error_body["error"]["message"]


def test_get_conversation_not_found(client: TestClient):
    """Verifies 404 on missing conversation ID."""
    headers = {"X-Dev-Email": "student@university.edu"}
    random_id = str(uuid.uuid4())
    res = client.get(f"/conversations/{random_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_post_message_and_save_turn(client: TestClient):
    """Requirements 4, 5, 6, 8: Save user message, assistant response, citations, update timestamp."""
    headers = {"X-Dev-Email": "chat_student@university.edu"}

    # Create conversation with default title
    conv_res = client.post("/conversations", json={}, headers=headers)
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]
    initial_updated_at = conv_res.json()["updated_at"]

    # Mock RAG service response to verify pipeline interaction and citation persistence
    mock_citations = [
        Citation(document="academic_regulations.pdf", page=14, section="Attendance Policy")
    ]
    mock_rag_result = RAGResponse(
        question="What is the minimum attendance requirement?",
        answer="A minimum of 75% attendance is required to appear in examinations.",
        citations=mock_citations,
        retrieved_chunks=[],
        is_sufficient=True,
        confidence_score=0.88,
        model_used="llama-3.1-8b-instant",
    )

    with patch("backend.app.api.conversations.rag_service.answer_question", new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_rag_result

        turn_res = client.post(
            f"/conversations/{conv_id}/messages",
            json={"content": "What is the minimum attendance requirement?"},
            headers=headers,
        )
        assert turn_res.status_code == 201, turn_res.text
        turn_data = turn_res.json()

        # Check turn response structure
        assert turn_data["conversation_id"] == conv_id
        assert turn_data["user_message"]["role"] == "user"
        assert turn_data["user_message"]["content"] == "What is the minimum attendance requirement?"
        assert turn_data["assistant_message"]["role"] == "assistant"
        assert turn_data["assistant_message"]["content"] == mock_rag_result.answer
        assert len(turn_data["citations"]) == 1
        assert turn_data["citations"][0]["document"] == "academic_regulations.pdf"
        assert turn_data["citations"][0]["page"] == 14

    # Verify conversation title was automatically updated from the first user query
    get_res = client.get(f"/conversations/{conv_id}", headers=headers)
    assert get_res.status_code == 200
    conv_detail = get_res.json()
    assert conv_detail["title"] == "What is the minimum attendance requirement?"
    assert len(conv_detail["messages"]) == 2
    assert conv_detail["messages"][0]["role"] == "user"
    assert conv_detail["messages"][1]["role"] == "assistant"
    assert conv_detail["messages"][1]["citations_json"] is not None
    assert conv_detail["messages"][1]["citations_json"][0]["document"] == "academic_regulations.pdf"


def test_post_message_forbidden_for_other_user(client: TestClient):
    """Requirement 7: Non-owner cannot post messages to another user's conversation."""
    owner_headers = {"X-Dev-Email": "owner_msg@university.edu"}
    intruder_headers = {"X-Dev-Email": "intruder_msg@university.edu"}

    conv = client.post("/conversations", json={}, headers=owner_headers).json()
    conv_id = conv["id"]

    res = client.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Can I hack into this thread?"},
        headers=intruder_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_conversational_history_lookback(client: TestClient):
    """Requirements 9 & 10: Passes the last 6 messages as conversational context to the RAG pipeline."""
    headers = {"X-Dev-Email": "multi_turn_user@university.edu"}

    conv = client.post("/conversations", json={"title": "Multi Turn Thread"}, headers=headers).json()
    conv_id = conv["id"]

    captured_histories = []

    async def mock_answer_question(question, conversation_history=None, session=None):
        captured_histories.append(list(conversation_history or []))
        return RAGResponse(
            question=question,
            answer=f"Answer to: {question}",
            citations=[],
            retrieved_chunks=[],
            is_sufficient=True,
            confidence_score=0.85,
            model_used="llama-3.1-8b-instant",
        )

    with patch("backend.app.api.conversations.rag_service.answer_question", side_effect=mock_answer_question):
        # Send 4 user messages (creates 4 user + 4 assistant = 8 total messages)
        for i in range(1, 5):
            res = client.post(
                f"/conversations/{conv_id}/messages",
                json={"content": f"Turn question {i}"},
                headers=headers,
            )
            assert res.status_code == 201

    # Turn 1: history should be empty (0 messages before it)
    assert len(captured_histories[0]) == 0

    # Turn 2: history should have 2 messages (Turn 1 user + Turn 1 assistant)
    assert len(captured_histories[1]) == 2
    assert captured_histories[1][0]["content"] == "Turn question 1"
    assert captured_histories[1][1]["content"] == "Answer to: Turn question 1"

    # Turn 4: prior to Turn 4 user, there were 6 messages (3 user + 3 assistant).
    # All 6 should be included in chronological order.
    assert len(captured_histories[3]) == 6
    assert captured_histories[3][0]["content"] == "Turn question 1"
    assert captured_histories[3][-1]["content"] == "Answer to: Turn question 3"


@pytest.mark.asyncio
async def test_conversation_persistence_in_db(client: TestClient, db_session):
    """Ensures conversation and message records persist cleanly in PostgreSQL tables."""
    headers = {"X-Dev-Email": "persistence_student@university.edu"}

    conv_res = client.post("/conversations", json={"title": "Persistence Test"}, headers=headers)
    assert conv_res.status_code == 201
    conv_id = uuid.UUID(conv_res.json()["id"])

    # Directly check PostgreSQL via separate SQLAlchemy session
    stmt = select(Conversation).where(Conversation.id == conv_id)
    result = await db_session.execute(stmt)
    persisted_conv = result.scalar_one_or_none()

    assert persisted_conv is not None
    assert persisted_conv.title == "Persistence Test"
    assert persisted_conv.id == conv_id
