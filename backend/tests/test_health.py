from fastapi.testclient import TestClient
from app.main import app

def test_root_endpoint():
    """Verify root endpoint returns welcome message and docs links."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "documentation" in data
        assert data["health_check"] == "/api/health"

def test_health_check_endpoint():
    """Verify health-check endpoint tests SQLite connection and returns healthy status."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["type"] == "SQLite"
        assert data["database"]["status"] == "connected"
        assert "cors_origins" in data
        assert "timestamp" in data

def test_database_tables_created():
    """Verify SQLAlchemy created all required SQLite tables on startup."""
    from sqlalchemy import inspect
    from app.database import engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "documents" in tables
    assert "document_chunks" in tables
    assert "chat_sessions" in tables
    assert "chat_messages" in tables
