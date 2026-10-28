"""Tests for persistent conversation history, continuation, ordering, access control, and migrations."""

from datetime import datetime, timezone
from importlib import import_module
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import CurrentUser, get_current_user
from app.database.base import Base
from app.database.models import ChatMessage, Conversation, Profile
from app.database.session import get_db
from app.main import app


@pytest.fixture
def in_memory_db():
    """Create a fresh in-memory SQLite database with all current models."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def auth_client(in_memory_db):
    """TestClient configured with in-memory DB and authenticated as user-1."""
    def override_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="citizen-user-1")

    with TestClient(app) as client:
        yield client, in_memory_db

    app.dependency_overrides.clear()


# --- Tests for Creation & Empty Conversations ---


def test_create_conversation_authenticated(auth_client):
    client, db = auth_client

    response = client.post(
        "/api/chat/conversations",
        json={"title": "Farming Subsidies", "language": "hi"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Farming Subsidies"
    assert data["language"] == "hi"
    assert data["message_count"] == 0
    assert "id" in data

    # Verify directly in database
    conv = db.get(Conversation, UUID(data["id"]))
    assert conv is not None
    assert conv.title == "Farming Subsidies"
    assert conv.language == "hi"


def test_create_conversation_default_values(auth_client):
    client, db = auth_client

    response = client.post("/api/chat/conversations", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Conversation"
    assert data["language"] == "en"
    assert data["message_count"] == 0


def test_get_empty_conversation(auth_client):
    client, db = auth_client

    # Create conversation
    create_res = client.post("/api/chat/conversations", json={"title": "Empty Test"})
    conv_id = create_res.json()["id"]

    # Get detail
    detail_res = client.get(f"/api/chat/conversations/{conv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == conv_id
    assert detail["title"] == "Empty Test"
    assert detail["messages"] == []


# --- Tests for Continuation, History & Ordering ---


def test_post_message_and_continuation_with_history(auth_client):
    client, db = auth_client

    # Create conversation
    conv_res = client.post("/api/chat/conversations", json={"language": "hi"})
    conv_id = conv_res.json()["id"]

    mock_sources = [
        {
            "id": 1,
            "scheme_title": "PM Kisan",
            "source_url": "https://pmkisan.gov.in",
            "publisher": "Ministry of Agriculture",
            "version_number": 1,
        }
    ]

    # First turn
    with patch(
        "app.api.chat.chat",
        return_value={
            "question": "PM किसान की अगली किस्त कब आएगी?",
            "answer": "पात्र किसानों को अगली किस्त सीधे बैंक खाते में दी जाएगी। [Source 1]",
            "generated_by": "gemini",
            "sources": mock_sources,
        },
    ) as chat_mock:
        msg_res1 = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"message": "PM किसान की अगली किस्त कब आएगी?"},
        )
        assert msg_res1.status_code == 200
        reply1 = msg_res1.json()
        assert reply1["role"] == "assistant"
        assert "[Source 1]" in reply1["content"]
        assert reply1["sources"][0]["scheme_title"] == "PM Kisan"

        # Verify chat() was called with empty prior history
        assert chat_mock.call_args.kwargs["history"] == []
        assert chat_mock.call_args.kwargs["language"] == "hi"

    # Second turn (continuation)
    with patch(
        "app.api.chat.chat",
        return_value={
            "question": "क्या e-KYC जरूरी है?",
            "answer": "हाँ, e-KYC अनिवार्य है।",
            "generated_by": "gemini",
            "sources": [],
        },
    ) as chat_mock2:
        msg_res2 = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"message": "क्या e-KYC जरूरी है?"},
        )
        assert msg_res2.status_code == 200

        # Verify prior turns (user + assistant) were passed as history
        passed_history = chat_mock2.call_args.kwargs["history"]
        assert len(passed_history) == 2
        assert passed_history[0]["role"] == "user"
        assert passed_history[0]["content"] == "PM किसान की अगली किस्त कब आएगी?"
        assert passed_history[1]["role"] == "assistant"
        assert "पात्र किसानों" in passed_history[1]["content"]

    # Verify chronological message ordering in conversation detail
    detail_res = client.get(f"/api/chat/conversations/{conv_id}")
    assert detail_res.status_code == 200
    messages = detail_res.json()["messages"]
    assert len(messages) == 4
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[0]["content"] == "PM किसान की अगली किस्त कब आएगी?"
    assert messages[2]["content"] == "क्या e-KYC जरूरी है?"


def test_list_conversations_ordering_and_counts(auth_client):
    client, db = auth_client

    # Create 3 conversations
    c1 = client.post("/api/chat/conversations", json={"title": "First"}).json()
    c2 = client.post("/api/chat/conversations", json={"title": "Second"}).json()
    c3 = client.post("/api/chat/conversations", json={"title": "Third"}).json()

    # Update conversation 1 by adding a message (bumps updated_at)
    with patch("app.api.chat.chat", return_value={"question": "q", "answer": "a", "generated_by": "fallback", "sources": []}):
        client.post(f"/api/chat/conversations/{c1['id']}/messages", json={"message": "Update first"})

    list_res = client.get("/api/chat/conversations")
    assert list_res.status_code == 200
    convs = list_res.json()
    assert len(convs) == 3
    # c1 was updated most recently, so it should be first
    assert convs[0]["id"] == c1["id"]
    assert convs[0]["message_count"] == 2  # user + assistant


# --- Tests for Unauthorized & Cross-User Access Control ---


def test_unauthenticated_requests_rejected(in_memory_db):
    """Endpoints require authentication when called without credentials."""
    def override_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as unauth_client:
        fake_id = uuid4()
        assert unauth_client.post("/api/chat/conversations", json={}).status_code == 401
        assert unauth_client.get("/api/chat/conversations").status_code == 401
        assert unauth_client.get(f"/api/chat/conversations/{fake_id}").status_code == 401
        assert unauth_client.post(f"/api/chat/conversations/{fake_id}/messages", json={"message": "hi"}).status_code == 401
        assert unauth_client.delete(f"/api/chat/conversations/{fake_id}").status_code == 401

    app.dependency_overrides.clear()


def test_cross_user_access_strictly_forbidden(in_memory_db):
    """User B must never access, message, or delete User A's conversations."""
    def override_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as test_client:
        # User A creates a conversation
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="citizen-A")
        conv_a = test_client.post("/api/chat/conversations", json={"title": "User A Private"}).json()
        conv_a_id = conv_a["id"]

        # Switch authentication to User B
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="citizen-B")

        # User B lists conversations -> must NOT see User A's conversation
        b_list = test_client.get("/api/chat/conversations").json()
        assert not any(c["id"] == conv_a_id for c in b_list)

        # User B attempts to read User A's conversation -> 403 Forbidden
        assert test_client.get(f"/api/chat/conversations/{conv_a_id}").status_code == 403

        # User B attempts to post message to User A's conversation -> 403 Forbidden
        assert test_client.post(
            f"/api/chat/conversations/{conv_a_id}/messages",
            json={"message": "Intrusion attempt"},
        ).status_code == 403

        # User B attempts to delete User A's conversation -> 403 Forbidden
        assert test_client.delete(f"/api/chat/conversations/{conv_a_id}").status_code == 403

    app.dependency_overrides.clear()


def test_nonexistent_conversation_returns_404(auth_client):
    client, db = auth_client
    non_existent = uuid4()
    assert client.get(f"/api/chat/conversations/{non_existent}").status_code == 404
    assert client.post(f"/api/chat/conversations/{non_existent}/messages", json={"message": "hello"}).status_code == 404
    assert client.delete(f"/api/chat/conversations/{non_existent}").status_code == 404


def test_delete_conversation_cascades(auth_client):
    client, db = auth_client

    conv = client.post("/api/chat/conversations", json={"title": "To Delete"}).json()
    conv_id = conv["id"]

    with patch("app.api.chat.chat", return_value={"question": "q", "answer": "a", "generated_by": "fallback", "sources": []}):
        client.post(f"/api/chat/conversations/{conv_id}/messages", json={"message": "msg"})

    del_res = client.delete(f"/api/chat/conversations/{conv_id}")
    assert del_res.status_code == 200

    # Verify conversation is gone
    assert client.get(f"/api/chat/conversations/{conv_id}").status_code == 404


# --- Migration & Schema Verification ---


def test_alembic_migration_schema_and_metadata():
    """Verify that the new migration file exists, is syntactically valid, and links correctly."""
    mod = import_module("migrations.versions.8f2c3b4e5d6a_add_conversations_and_chat_messages")

    assert mod.revision == "8f2c3b4e5d6a"
    assert mod.down_revision == "8683abb215e8"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")


# --- Hardening Tests: Rollback on Failure & Serialization ---


def test_send_message_rollback_on_chatbot_failure(auth_client):
    """When the chatbot/RAG service raises an error, no message is committed and session rolls back."""
    client, db = auth_client

    conv = client.post("/api/chat/conversations", json={"title": "Rollback Test"}).json()
    conv_id = conv["id"]

    with patch("app.api.chat.chat", side_effect=RuntimeError("Simulated LLM network error")):
        with pytest.raises(RuntimeError, match="Simulated LLM network error"):
            client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"message": "This message should not be committed"},
            )

    # Verify no message was persisted (zero messages in conversation)
    detail_res = client.get(f"/api/chat/conversations/{conv_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["messages"] == []

    # Verify database directly contains 0 messages for this conversation
    messages = db.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == UUID(conv_id))
    ).all()
    assert len(messages) == 0


def test_send_message_rollback_on_commit_failure(auth_client):
    """When database commit fails, the transaction is rolled back cleanly."""
    client, db = auth_client

    conv = client.post("/api/chat/conversations", json={"title": "Commit Failure Test"}).json()
    conv_id = conv["id"]

    with patch("app.api.chat.chat", return_value={"question": "q", "answer": "a", "generated_by": "fallback", "sources": []}):
        with patch.object(db, "commit", side_effect=RuntimeError("Simulated database failure")):
            with pytest.raises(RuntimeError, match="Simulated database failure"):
                client.post(
                    f"/api/chat/conversations/{conv_id}/messages",
                    json={"message": "Will fail commit"},
                )

    # Verify no partial turn was saved
    detail_res = client.get(f"/api/chat/conversations/{conv_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["messages"] == []


def test_serialized_consecutive_messages_maintain_exact_order(auth_client):
    """Multiple turns correctly acquire lock, read accumulated history, and maintain exact order."""
    client, db = auth_client

    conv = client.post("/api/chat/conversations", json={"language": "en"}).json()
    conv_id = conv["id"]

    history_snapshots = []

    def mock_chat(db, question, history, language):
        history_snapshots.append(list(history))
        return {
            "question": question,
            "answer": f"Answer to {question}",
            "generated_by": "test",
            "sources": [],
        }

    with patch("app.api.chat.chat", side_effect=mock_chat):
        client.post(f"/api/chat/conversations/{conv_id}/messages", json={"message": "Turn 1"})
        client.post(f"/api/chat/conversations/{conv_id}/messages", json={"message": "Turn 2"})
        client.post(f"/api/chat/conversations/{conv_id}/messages", json={"message": "Turn 3"})

    # Check history passed to each turn:
    # Turn 1: history was empty
    assert len(history_snapshots[0]) == 0
    # Turn 2: history contained Turn 1 user + Turn 1 assistant
    assert len(history_snapshots[1]) == 2
    assert history_snapshots[1][0]["content"] == "Turn 1"
    # Turn 3: history contained Turn 1 & Turn 2 (4 messages)
    assert len(history_snapshots[2]) == 4
    assert history_snapshots[2][2]["content"] == "Turn 2"

    # Verify conversation message count and ordering
    detail_res = client.get(f"/api/chat/conversations/{conv_id}")
    messages = detail_res.json()["messages"]
    assert len(messages) == 6
    assert [m["content"] for m in messages if m["role"] == "user"] == ["Turn 1", "Turn 2", "Turn 3"]
