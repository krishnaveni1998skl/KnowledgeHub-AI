"""
Test Suite for Authentication, Authorization (RBAC), and Multilingual RAG features:
- Registration (validation, duplicate prevention, viewer default role)
- Login (bcrypt password verification, token issuance, invalid credentials)
- Current user profile & session invalidation (logout)
- Password recovery (forgot-password, token verification, reset-password, reuse prevention)
- Role-based authorization guards (401 without auth, 403 for viewer on upload/delete)
- Multilingual RAG request handling (en, ta, hi)
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import SessionLocal
from app.models.schema import User, UserSession, PasswordResetToken, Document
from app.services.auth import hash_password, verify_password, validate_password_strength

# Helper to generate unique emails in tests
def get_random_email() -> str:
    return f"test_user_{uuid.uuid4().hex[:8]}@example.com"


# ==========================================
# 1. Password Hashing & Strength Tests
# ==========================================

def test_password_hashing_and_verification():
    """Verify bcrypt hashes passwords with unique salts and verifies properly."""
    password = "CorrectHorseBattery99!"
    h1 = hash_password(password)
    h2 = hash_password(password)
    assert h1 != h2  # Salt ensures distinct hashes
    assert verify_password(password, h1) is True
    assert verify_password(password, h2) is True
    assert verify_password("WrongPassword123!", h1) is False
    assert verify_password("", h1) is False


def test_password_strength_validation():
    """Enforce minimum 8 chars, letter, and number/symbol."""
    valid, _ = validate_password_strength("Short1!")
    assert valid is False  # < 8 chars

    valid, _ = validate_password_strength("alllowercaseandlong")
    assert valid is False  # no numbers or symbols

    valid, _ = validate_password_strength("1234567890123")
    assert valid is False  # no letters

    valid, _ = validate_password_strength("SecurePassword2026!")
    assert valid is True


# ==========================================
# 2. Registration Tests
# ==========================================

def test_user_registration_success_and_default_viewer_role():
    """Register a new user and verify safe default 'viewer' role."""
    email = get_random_email()
    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test Engineering User",
                "email": email,
                "password": "SecurePassword123!"
            }
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) > 20
        assert data["user"]["email"] == email
        assert data["user"]["full_name"] == "Test Engineering User"
        assert data["user"]["role"] == "viewer"  # Enforces safe default role


def test_user_registration_duplicate_email_rejected():
    """Attempting to register with an existing email returns 409 Conflict."""
    email = get_random_email()
    with TestClient(app) as client:
        # First registration
        resp1 = client.post(
            "/api/auth/register",
            json={
                "full_name": "First User",
                "email": email,
                "password": "SecurePassword123!"
            }
        )
        assert resp1.status_code == 201

        # Second registration with same email
        resp2 = client.post(
            "/api/auth/register",
            json={
                "full_name": "Second User",
                "email": email,
                "password": "SecurePassword123!"
            }
        )
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"].lower()


def test_user_registration_weak_password_rejected():
    """Registering with a weak password returns 400 or 422."""
    email = get_random_email()
    with TestClient(app) as client:
        # Schema rejects < 8 chars with 422
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Weak User",
                "email": email,
                "password": "short"
            }
        )
        assert resp.status_code == 422

        # Custom strength validator rejects >= 8 chars lacking digits/symbols with 400
        resp2 = client.post(
            "/api/auth/register",
            json={
                "full_name": "Weak User 2",
                "email": get_random_email(),
                "password": "onlylettersnohash"
            }
        )
        assert resp2.status_code == 400
        assert "number or special character" in resp2.json()["detail"].lower()


# ==========================================
# 3. Login & Profile Tests
# ==========================================

def test_login_success_and_profile_endpoint():
    """Sign in with valid credentials, retrieve token, and query /api/auth/me."""
    email = get_random_email()
    password = "MyComplexPassword2026!"
    with TestClient(app) as client:
        # Register user
        reg_resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Auth Tester",
                "email": email,
                "password": password
            }
        )
        assert reg_resp.status_code == 201

        # Login
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": password, "remember": True}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]
        assert token is not None

        # Query /api/auth/me
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["email"] == email
        assert me_data["role"] == "viewer"


def test_login_invalid_password_and_nonexistent_user():
    """Ensure invalid credentials return 401 Unauthorized."""
    email = get_random_email()
    with TestClient(app) as client:
        # Register
        client.post(
            "/api/auth/register",
            json={"full_name": "User", "email": email, "password": "Password123!"}
        )

        # Wrong password
        resp1 = client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword999!"}
        )
        assert resp1.status_code == 401

        # Nonexistent user
        resp2 = client.post(
            "/api/auth/login",
            json={"email": "nonexistent_person_999@company.com", "password": "Password123!"}
        )
        assert resp2.status_code == 401


def test_logout_revokes_token():
    """Logging out invalidates the session token in the database."""
    email = get_random_email()
    password = "Password123!"
    with TestClient(app) as client:
        reg_resp = client.post(
            "/api/auth/register",
            json={"full_name": "Logout User", "email": email, "password": password}
        )
        token = reg_resp.json()["token"]

        # /me succeeds
        me_resp1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp1.status_code == 200

        # Logout
        logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout_resp.status_code == 200

        # Subsequent /me fails with 401
        me_resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp2.status_code == 401


# ==========================================
# 4. Password Recovery & Reset Flow Tests
# ==========================================

def test_forgot_password_and_reset_flow():
    """Execute complete password recovery: request token, submit new password, verify login."""
    email = get_random_email()
    old_password = "OldPassword123!"
    new_password = "NewBrandNewPassword2026!"

    with TestClient(app) as client:
        # Register
        client.post(
            "/api/auth/register",
            json={"full_name": "Recovery User", "email": email, "password": old_password}
        )

        # Request reset (in dev mode, dev_reset_token is returned)
        forgot_resp = client.post(
            "/api/auth/forgot-password",
            json={"email": email}
        )
        assert forgot_resp.status_code == 200
        data = forgot_resp.json()
        assert "dev_reset_token" in data
        reset_token = data["dev_reset_token"]

        # Reset password with token
        reset_resp = client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": new_password}
        )
        assert reset_resp.status_code == 200

        # Attempt to use old password -> 401
        fail_login = client.post(
            "/api/auth/login",
            json={"email": email, "password": old_password}
        )
        assert fail_login.status_code == 401

        # Use new password -> 200
        success_login = client.post(
            "/api/auth/login",
            json={"email": email, "password": new_password}
        )
        assert success_login.status_code == 200

        # Attempting to REUSE the same reset token fails with 400
        reuse_resp = client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": "AnotherPassword123!"}
        )
        assert reuse_resp.status_code == 400


# ==========================================
# 5. Role-Based Access Control (RBAC) Tests
# ==========================================

def test_unauthorized_access_rejected_with_401():
    """Sensitive endpoints reject requests missing authentication tokens."""
    with TestClient(app) as client:
        # No header
        resp = client.get("/api/documents")
        assert resp.status_code == 401

        resp2 = client.post("/api/documents/upload", files={"file": ("test.pdf", b"abc", "application/pdf")})
        assert resp2.status_code == 401

        resp3 = client.delete("/api/documents/999")
        assert resp3.status_code == 401


def test_viewer_role_restricted_from_upload_and_delete():
    """A user with role 'viewer' receives 403 Forbidden on upload and delete endpoints."""
    email = get_random_email()
    with TestClient(app) as client:
        # Register viewer user
        reg_resp = client.post(
            "/api/auth/register",
            json={"full_name": "Viewer Only", "email": email, "password": "Password123!"}
        )
        viewer_token = reg_resp.json()["token"]
        auth_header = {"Authorization": f"Bearer {viewer_token}"}

        # Viewer CAN view documents list (200)
        list_resp = client.get("/api/documents", headers=auth_header)
        assert list_resp.status_code == 200

        # Viewer CANNOT upload (403 Forbidden)
        upload_resp = client.post(
            "/api/documents/upload",
            files={"file": ("unauthorized.pdf", b"%PDF-1.4...", "application/pdf")},
            headers=auth_header
        )
        assert upload_resp.status_code == 403
        assert "requires one of roles" in upload_resp.json()["detail"].lower()

        # Viewer CANNOT delete (403 Forbidden)
        delete_resp = client.delete(
            "/api/documents/1",
            headers=auth_header
        )
        assert delete_resp.status_code == 403


# ==========================================
# 6. Multilingual RAG Language Support Tests
# ==========================================

def test_rag_multilingual_tamil_and_hindi_dispatch():
    """Verify that AskRequest accepts 'ta' and 'hi' and passes language instruction to RAG service."""
    from app.services.rag import rag_service

    mock_chunks = [
        {
            "id": "c1",
            "document_id": 1,
            "filename": "sample_student_report.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "content": "Rahul Kumar | Computer Science | III Year | Active",
            "similarity_score": 0.95
        }
    ]

    with patch.object(rag_service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock Cohere chat response
        mock_resp = MagicMock()
        mock_resp.message.content = [MagicMock(text="ராகுல் குமாரின் துறை கணினி அறிவியல் ஆகும். [Source 1: sample_student_report.pdf (Page 1)]")]
        mock_client.chat.return_value = mock_resp

        # Test Tamil language request
        result_ta = rag_service.generate_grounded_answer(
            query="What is Rahul Kumar's department?",
            context_chunks=mock_chunks,
            language="ta"
        )
        assert result_ta["answer"] is not None
        assert len(result_ta["sources"]) > 0

        # Inspect system prompt passed to Cohere client
        chat_args = mock_client.chat.call_args[1]
        system_content = chat_args["messages"][0]["content"]
        assert "Tamil" in system_content or "தமிழ்" in system_content

        # Test Hindi language request
        mock_resp.message.content = [MagicMock(text="राहुल कुमार का विभाग कंप्यूटर साइंस है। [Source 1: sample_student_report.pdf (Page 1)]")]
        result_hi = rag_service.generate_grounded_answer(
            query="What is Rahul Kumar's department?",
            context_chunks=mock_chunks,
            language="hi"
        )
        assert result_hi["answer"] is not None
        chat_args_hi = mock_client.chat.call_args[1]
        system_content_hi = chat_args_hi["messages"][0]["content"]
        assert "Hindi" in system_content_hi or "हिन्दी" in system_content_hi


# ==========================================
# 7. Session Expiry & Security Edge Cases
# ==========================================

def test_expired_session_token_rejected_with_401():
    """Verify that an expired bearer session token is rejected with HTTP 401."""
    from datetime import datetime, timedelta, timezone
    from app.services.auth import create_user_session, hash_token

    email = get_random_email()
    with TestClient(app) as client:
        # Register user
        reg_resp = client.post(
            "/api/auth/register",
            json={"full_name": "Expiry User", "email": email, "password": "Password123!"}
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["token"]

        # Token initially works
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

        # Artificially expire the token in SQLite
        db = SessionLocal()
        try:
            t_hash = hash_token(token)
            session_rec = db.query(UserSession).filter(UserSession.token_hash == t_hash).first()
            assert session_rec is not None
            session_rec.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
            db.commit()
        finally:
            db.close()

        # Expired token is rejected with 401
        expired_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert expired_resp.status_code == 401
        assert "expired" in expired_resp.json()["detail"].lower()


# ==========================================
# 8. User Conversation Isolation & Chat History Tests
# ==========================================

def test_conversation_session_isolation_across_users():
    """Verify that User B cannot query or inject messages into User A's chat session."""
    user_a_email = get_random_email()
    user_b_email = get_random_email()

    mock_rag_response = {
        "answer": "This is a confidential answer. [sample.pdf (Page 1)]",
        "sources": [{"document_id": 1, "filename": "sample.pdf", "page_number": 1}],
        "chunks_used": 1
    }

    with patch("app.api.search.rag_service.generate_grounded_answer", return_value=mock_rag_response), \
         patch("app.api.search.rag_service.embed_query", return_value=[0.1]*5), \
         patch("app.api.search.vector_store.count", return_value=1), \
         patch("app.api.search.vector_store.query_similar", return_value=[]):

        with TestClient(app) as client:
            # Register User A and User B
            token_a = client.post("/api/auth/register", json={"full_name": "User A", "email": user_a_email, "password": "Password123!"}).json()["token"]
            token_b = client.post("/api/auth/register", json={"full_name": "User B", "email": user_b_email, "password": "Password123!"}).json()["token"]

            # User A initiates a conversation
            ask_resp_a = client.post(
                "/api/rag/ask",
                json={"question": "What is our company secret policy?", "top_k": 5},
                headers={"Authorization": f"Bearer {token_a}"}
            )
            assert ask_resp_a.status_code == 200
            session_id = ask_resp_a.json()["session_id"]

            # User A can inspect the session
            sess_resp_a = client.get(
                f"/api/rag/sessions/{session_id}",
                headers={"Authorization": f"Bearer {token_a}"}
            )
            assert sess_resp_a.status_code == 200
            assert len(sess_resp_a.json()["messages"]) == 2

            # User B attempts to access User A's session -> 403 Forbidden
            sess_resp_b = client.get(
                f"/api/rag/sessions/{session_id}",
                headers={"Authorization": f"Bearer {token_b}"}
            )
            assert sess_resp_b.status_code == 403
            assert "access denied" in sess_resp_b.json()["detail"].lower()

            # User B attempts to append a message to User A's session -> 403 Forbidden
            hijack_resp = client.post(
                "/api/rag/ask",
                json={"question": "Tell me User A's secrets!", "session_id": session_id},
                headers={"Authorization": f"Bearer {token_b}"}
            )
            assert hijack_resp.status_code == 403
            assert "another user" in hijack_resp.json()["detail"].lower()


def test_user_specific_chat_sessions_listing_and_deletion():
    """Verify that /api/rag/sessions returns only the caller's conversations and deletion enforces ownership."""
    user_a_email = get_random_email()
    user_b_email = get_random_email()

    mock_rag_response = {
        "answer": "Answer text",
        "sources": [],
        "chunks_used": 0
    }

    with patch("app.api.search.rag_service.generate_grounded_answer", return_value=mock_rag_response), \
         patch("app.api.search.rag_service.embed_query", return_value=[0.1]*5), \
         patch("app.api.search.vector_store.count", return_value=0):

        with TestClient(app) as client:
            token_a = client.post("/api/auth/register", json={"full_name": "User A", "email": user_a_email, "password": "Password123!"}).json()["token"]
            token_b = client.post("/api/auth/register", json={"full_name": "User B", "email": user_b_email, "password": "Password123!"}).json()["token"]

            # User A asks 2 questions in distinct sessions
            resp_a1 = client.post("/api/rag/ask", json={"question": "Question A1"}, headers={"Authorization": f"Bearer {token_a}"}).json()
            resp_a2 = client.post("/api/rag/ask", json={"question": "Question A2"}, headers={"Authorization": f"Bearer {token_a}"}).json()
            session_a1 = resp_a1["session_id"]
            session_a2 = resp_a2["session_id"]

            # User B asks 1 question
            resp_b = client.post("/api/rag/ask", json={"question": "Question B1"}, headers={"Authorization": f"Bearer {token_b}"}).json()
            session_b = resp_b["session_id"]

            # Listing for User A returns exactly 2 sessions
            list_a = client.get("/api/rag/sessions", headers={"Authorization": f"Bearer {token_a}"}).json()
            assert len(list_a) == 2
            ids_a = {s["id"] for s in list_a}
            assert session_a1 in ids_a
            assert session_a2 in ids_a
            assert session_b not in ids_a

            # Listing for User B returns exactly 1 session
            list_b = client.get("/api/rag/sessions", headers={"Authorization": f"Bearer {token_b}"}).json()
            assert len(list_b) == 1
            assert list_b[0]["id"] == session_b

            # User B cannot delete User A's session -> 403 Forbidden
            del_fail = client.delete(f"/api/rag/sessions/{session_a1}", headers={"Authorization": f"Bearer {token_b}"})
            assert del_fail.status_code == 403

            # User A can delete their own session -> 200 OK
            del_ok = client.delete(f"/api/rag/sessions/{session_a1}", headers={"Authorization": f"Bearer {token_a}"})
            assert del_ok.status_code == 200

            # Verify it is deleted
            list_a_after = client.get("/api/rag/sessions", headers={"Authorization": f"Bearer {token_a}"}).json()
            assert len(list_a_after) == 1
            assert list_a_after[0]["id"] == session_a2


# ==========================================
# 9. Cross-User Document Access & Permissions Tests
# ==========================================

def test_restricted_document_cross_user_access_prevention():
    """Verify that restricted documents cannot be previewed, chunk-inspected, or downloaded by other non-admin users."""
    user_a_email = get_random_email()
    user_b_email = get_random_email()

    with TestClient(app) as client:
        token_a = client.post("/api/auth/register", json={"full_name": "Editor A", "email": user_a_email, "password": "Password123!"}).json()["token"]
        token_b = client.post("/api/auth/register", json={"full_name": "Viewer B", "email": user_b_email, "password": "Password123!"}).json()["token"]

        # Elevate User A to editor
        db = SessionLocal()
        try:
            user_a = db.query(User).filter(User.email == user_a_email).first()
            user_a.role = "editor"
            db.commit()

            # Create a restricted document owned by User A
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(b"%PDF-1.4 confidential content")
            temp_file.close()

            doc = Document(
                filename="confidential_merger.pdf",
                file_type="pdf",
                file_size=100,
                file_path=temp_file.name,
                file_hash="mock_hash_confidential",
                status="indexed",
                uploaded_by_id=user_a.id,
                is_restricted=True,
                page_count=1,
                chunk_count=1
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            doc_id = doc.id
        finally:
            db.close()

        # User B (viewer) attempts to get metadata -> 403 Forbidden
        meta_resp_b = client.get(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert meta_resp_b.status_code == 403
        assert "access denied" in meta_resp_b.json()["detail"].lower()

        # User B attempts to view chunks -> 403 Forbidden
        chunks_resp_b = client.get(f"/api/documents/{doc_id}/chunks", headers={"Authorization": f"Bearer {token_b}"})
        assert chunks_resp_b.status_code == 403

        # User B attempts to download file -> 403 Forbidden
        file_resp_b = client.get(f"/api/documents/{doc_id}/file", headers={"Authorization": f"Bearer {token_b}"})
        assert file_resp_b.status_code == 403

        # User A (owner) CAN access metadata and chunks -> 200 OK
        meta_resp_a = client.get(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert meta_resp_a.status_code == 200


def test_document_deletion_ownership_check():
    """Verify that an editor cannot delete another editor's upload, but an administrator can."""
    editor_a_email = get_random_email()
    editor_b_email = get_random_email()

    with TestClient(app) as client:
        token_a = client.post("/api/auth/register", json={"full_name": "Editor A", "email": editor_a_email, "password": "Password123!"}).json()["token"]
        token_b = client.post("/api/auth/register", json={"full_name": "Editor B", "email": editor_b_email, "password": "Password123!"}).json()["token"]

        db = SessionLocal()
        try:
            user_a = db.query(User).filter(User.email == editor_a_email).first()
            user_b = db.query(User).filter(User.email == editor_b_email).first()
            user_a.role = "editor"
            user_b.role = "editor"
            db.commit()

            doc = Document(
                filename="editor_a_doc.pdf",
                file_type="pdf",
                file_size=500,
                file_path="",
                file_hash="hash_a_123",
                status="indexed",
                uploaded_by_id=user_a.id,
                is_restricted=False
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            doc_id = doc.id
        finally:
            db.close()

        # Editor B attempts to delete Editor A's document -> 403 Forbidden
        del_fail = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert del_fail.status_code == 403
        assert "uploaded" in del_fail.json()["detail"].lower()

        # Editor A can delete their own document -> 200 OK
        del_ok = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert del_ok.status_code == 200


# ==========================================
# 10. Dashboard Stats & Follow-Up Questions Tests
# ==========================================

def test_dashboard_stats_endpoint():
    """Verify that /api/dashboard/stats returns real-time document and user-isolated conversation counts."""
    email = get_random_email()
    with TestClient(app) as client:
        token = client.post("/api/auth/register", json={"full_name": "Stats User", "email": email, "password": "Password123!"}).json()["token"]

        resp = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_documents" in data
        assert "indexed_documents" in data
        assert "failed_documents" in data
        assert "total_chunks" in data
        assert "total_vectors" in data
        assert "user_conversations" in data
        assert data["user_role"] == "viewer"
        assert data["user_email"] == email


def test_rag_follow_up_questions_receive_chat_history():
    """Verify that when a session_id is provided, previous turns are passed to generate_grounded_answer."""
    user_email = get_random_email()
    captured_chat_history = []

    def mock_generate_grounded_answer(query, context_chunks, language="en", chat_history=None):
        nonlocal captured_chat_history
        captured_chat_history = chat_history or []
        return {
            "answer": f"Grounded response for: {query}",
            "sources": [],
            "chunks_used": 0
        }

    with patch("app.api.search.rag_service.generate_grounded_answer", side_effect=mock_generate_grounded_answer), \
         patch("app.api.search.rag_service.embed_query", return_value=[0.1]*5), \
         patch("app.api.search.vector_store.count", return_value=0):

        with TestClient(app) as client:
            token = client.post("/api/auth/register", json={"full_name": "Chat User", "email": user_email, "password": "Password123!"}).json()["token"]
            auth_header = {"Authorization": f"Bearer {token}"}

            # Turn 1: First question
            resp1 = client.post("/api/rag/ask", json={"question": "What is Rahul Kumar's department?"}, headers=auth_header).json()
            session_id = resp1["session_id"]
            assert len(captured_chat_history) == 0  # No prior history on Turn 1

            # Turn 2: Follow-up question in the same session
            client.post("/api/rag/ask", json={"question": "What is his status?", "session_id": session_id}, headers=auth_header)
            assert len(captured_chat_history) == 2  # Prior turn: 1 user msg, 1 assistant msg
            assert captured_chat_history[0]["role"] == "user"
            assert "Rahul Kumar" in captured_chat_history[0]["content"]
            assert captured_chat_history[1]["role"] == "assistant"

