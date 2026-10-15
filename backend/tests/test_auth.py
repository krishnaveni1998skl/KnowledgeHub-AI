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
from app.models.schema import User, UserSession, PasswordResetToken
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
