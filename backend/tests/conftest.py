"""
Pytest configuration and fixtures for KnowledgeHub AI backend test suite.
Ensures legacy functional tests (ingestion, chunking, vector rag) retain admin authentication,
while dedicated authentication test suite (test_auth.py) executes against real unmocked auth logic.
"""
import pytest
from app.main import app
from app.api.auth import get_current_user, require_roles
from app.api.documents import get_user_from_token_or_query
from app.models.schema import User

@pytest.fixture(autouse=True)
def auth_fixture_for_tests(request):
    """
    If running test_auth.py, do NOT override auth (test real auth).
    For other legacy tests, override get_current_user and get_user_from_token_or_query to simulate an authenticated admin.
    """
    if "test_auth" in request.module.__name__:
        yield
    else:
        # Create an in-memory mock admin user for existing tests
        mock_admin = User(
            id=1,
            email="admin@knowledgehub.ai",
            full_name="KnowledgeHub Administrator",
            role="admin",
            is_active=True
        )
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        app.dependency_overrides[get_user_from_token_or_query] = lambda: mock_admin
        try:
            yield
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_from_token_or_query, None)
