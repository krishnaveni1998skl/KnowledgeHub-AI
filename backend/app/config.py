from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    API_ENV: str = "development"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # CORS configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173"

    # SQLite Database
    DATABASE_URL: str = "sqlite:///./data/knowledgehub.db"

    # Storage paths
    UPLOAD_DIRECTORY: str = "./data/uploads"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"

    # Upload and Document Processing Settings
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx"]
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TESSERACT_CMD: str = ""

    # Cohere API configuration
    COHERE_API_KEY: str = ""
    COHERE_EMBED_MODEL: str = "embed-english-v3.0"
    COHERE_CHAT_MODEL: str = "command-r-08-2024"
    COHERE_EMBED_BATCH_SIZE: int = 96

    # ChromaDB Collection Settings
    CHROMA_COLLECTION_NAME: str = "knowledgehub_documents"

    # Authentication & Security Settings
    SESSION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60
    INITIAL_ADMIN_EMAIL: str = "admin@knowledgehub.ai"
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_NAME: str = "KnowledgeHub Administrator"

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def resolved_upload_dir(self) -> Path:
        upload_path = Path(self.UPLOAD_DIRECTORY)
        if not upload_path.is_absolute():
            upload_path = (BACKEND_DIR / upload_path).resolve()
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    @property
    def resolved_chroma_dir(self) -> Path:
        chroma_path = Path(self.CHROMA_PERSIST_DIRECTORY)
        if not chroma_path.is_absolute():
            chroma_path = (BACKEND_DIR / chroma_path).resolve()
        chroma_path.mkdir(parents=True, exist_ok=True)
        return chroma_path

    @property
    def is_cohere_configured(self) -> bool:
        key = (self.COHERE_API_KEY or "").strip()
        return bool(key and key != "your_cohere_api_key_here")

settings = Settings()
