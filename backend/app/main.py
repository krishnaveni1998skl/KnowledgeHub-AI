import os
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
import app.models  # Register models with Base.metadata for table creation
from app.api import health_router, documents_router, search_router, auth_router
from app.services.auth import ensure_initial_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure SQLite tables exist
    Base.metadata.create_all(bind=engine)

    # Auto-migrate SQLite columns if table was created in an earlier phase
    with engine.connect() as conn:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "documents" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("documents")}
            if "chunk_count" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0"))
            if "error_message" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN error_message TEXT"))
            if "file_hash" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"))
            conn.commit()

            # Backfill file_hash for existing files on disk if null
            try:
                rows = conn.execute(text("SELECT id, file_path FROM documents WHERE file_hash IS NULL")).fetchall()
                for row_id, file_path in rows:
                    if file_path and os.path.isfile(file_path):
                        with open(file_path, "rb") as f:
                            h = hashlib.sha256(f.read()).hexdigest()
                        conn.execute(text("UPDATE documents SET file_hash = :h WHERE id = :id"), {"h": h, "id": row_id})
                conn.commit()
            except Exception:
                pass

    # Ensure required data folders exist
    backend_dir = Path(__file__).resolve().parent.parent
    uploads_path = (backend_dir / settings.UPLOAD_DIRECTORY).resolve()
    chroma_path = (backend_dir / settings.CHROMA_PERSIST_DIRECTORY).resolve()
    uploads_path.mkdir(parents=True, exist_ok=True)
    chroma_path.mkdir(parents=True, exist_ok=True)
    # Ensure initial administrator exists
    try:
        with SessionLocal() as db_session:
            ensure_initial_admin(db_session)
    except Exception as e:
        pass

    yield
    # Shutdown logic if any

app = FastAPI(
    title="KnowledgeHub AI API",
    description="Intelligent Company Document Assistant Backend using FastAPI, SQLite, and Cohere RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for React frontend (Vite running on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to KnowledgeHub AI Backend API",
        "documentation": "/docs",
        "health_check": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
