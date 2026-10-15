import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint: verifies API server, SQLite database connectivity,
    and reports configuration status.
    """
    # Test SQLite database query
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    vector_store_status = "unavailable"
    vector_count = 0
    try:
        from app.services.vector_store import vector_store
        vector_count = vector_store.count()
        vector_store_status = "connected"
    except Exception as e:
        vector_store_status = f"error: {str(e)}"

    cohere_configured = bool(settings.COHERE_API_KEY and settings.COHERE_API_KEY.strip() != "your_cohere_api_key_here")

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "KnowledgeHub AI Backend",
        "version": "1.0.0",
        "environment": settings.API_ENV,
        "database": {
            "type": "SQLite",
            "status": db_status
        },
        "vector_store": {
            "type": "ChromaDB",
            "status": vector_store_status,
            "total_vectors": vector_count
        },
        "cors_origins": settings.cors_origins_list,
        "cohere_configured": cohere_configured,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
