"""
Document management and ingestion API router.
Provides endpoints for uploading, extracting, chunking, and listing documents.
"""
import os
import re
import uuid
import logging
import hashlib
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Header, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.schema import Document, DocumentChunk, User
from app.services.extractor import extract_text_from_pdf, extract_text_from_docx
from app.services.chunker import chunk_document
from app.services.vector_store import vector_store
from app.services.indexer import index_document_chunks, reprocess_and_index_document
from app.api.auth import get_current_user, require_roles
from app.services.auth import get_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream", # Some browsers send this for binary uploads
}

def sanitize_filename(filename: str) -> str:
    """Removes path traversal attempts and special characters from filename."""
    # Strip any directory pathing (e.g., ../../evil.pdf -> evil.pdf)
    base_name = Path(filename).name.strip()
    if not base_name or base_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename."
        )
    # Sanitize characters
    cleaned = re.sub(r'[^a-zA-Z0-9_.\- ]', '_', base_name)
    return cleaned

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "editor"]))
):
    """
    Upload and ingest a PDF or DOCX file:
    1. Validates extension, MIME type, and non-empty content.
    2. Enforces maximum file size and path traversal protection.
    3. Saves safely to data/uploads.
    4. Extracts text page-by-page (PyMuPDF with OCR fallback / python-docx).
    5. Cleans and chunks text with page citation metadata.
    6. Stores metadata and chunks in SQLite.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    safe_original_name = sanitize_filename(file.filename)
    extension = Path(safe_original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{extension}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Unusual MIME type received: {file.content_type} for {safe_original_name}")

    # Generate unique storage filename to avoid collision and execution
    unique_storage_name = f"{uuid.uuid4().hex[:12]}_{safe_original_name}"
    upload_dir = settings.resolved_upload_dir
    target_path = upload_dir / unique_storage_name

    # Read and stream file with size validation and SHA-256 hash computation
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0
    hasher = hashlib.sha256()

    try:
        with open(target_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024): # 1MB chunks
                total_bytes += len(chunk)
                hasher.update(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        if target_path.exists():
            target_path.unlink()
        raise
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving uploaded file: {str(e)}"
        )

    if total_bytes == 0:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    file_hash = hasher.hexdigest()

    # Content-hash duplicate detection: Prevent duplicate records and duplicate ChromaDB vectors
    existing_doc = db.query(Document).filter(
        Document.file_hash == file_hash,
        Document.status == "indexed"
    ).first()

    if existing_doc:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate document detected: Content is identical to already indexed document '{existing_doc.filename}' (Document ID: {existing_doc.id})."
        )

    # Create initial Document record in SQLite
    doc_record = Document(
        filename=safe_original_name,
        file_type=extension.replace(".", ""),
        file_size=total_bytes,
        file_path=str(target_path),
        file_hash=file_hash,
        status="processing",
        page_count=0,
        chunk_count=0,
        extraction_method="direct"
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # Ingestion Pipeline: Extract & Chunk
    try:
        if extension == ".pdf":
            extraction = extract_text_from_pdf(str(target_path))
        else: # .docx
            extraction = extract_text_from_docx(str(target_path))

        pages = extraction.get("pages", [])
        page_count = extraction.get("page_count", 1)
        extraction_method = extraction.get("extraction_method", "direct")

        # Chunk pages while preserving page citations
        chunks = chunk_document(
            pages,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        if not chunks:
            raise ValueError("No readable text could be extracted or chunked from this document.")

        # Save chunks to SQLite
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=doc_record.id,
                chunk_index=chunk["chunk_index"],
                page_number=chunk["page_number"],
                content=chunk["content"],
                token_count=chunk["token_count"]
            )
            db.add(db_chunk)

        # Update document record to indexed (processed)
        doc_record.status = "indexed"
        doc_record.page_count = page_count
        doc_record.chunk_count = len(chunks)
        doc_record.extraction_method = extraction_method
        doc_record.error_message = None
        db.commit()
        db.refresh(doc_record)

        # Auto-index vectors into ChromaDB if Cohere is configured
        if settings.is_cohere_configured:
            try:
                index_document_chunks(doc_record.id, db)
            except Exception as idx_err:
                logger.warning(f"Vector indexing skipped/failed during upload for doc {doc_record.id}: {idx_err}")

        return {
            "id": doc_record.id,
            "filename": doc_record.filename,
            "file_type": doc_record.file_type,
            "file_size": doc_record.file_size,
            "file_hash": doc_record.file_hash,
            "status": doc_record.status,
            "page_count": doc_record.page_count,
            "chunk_count": doc_record.chunk_count,
            "extraction_method": doc_record.extraction_method,
            "message": "Document ingested and chunked successfully."
        }

    except Exception as exc:
        logger.error(f"Failed to ingest document ID {doc_record.id}: {exc}", exc_info=True)
        sanitized_msg = re.sub(r"[A-Za-z]:\\[^ \t\n\r\f\v'\"]+", "[file]", str(exc))
        doc_record.status = "failed"
        doc_record.error_message = sanitized_msg
        db.commit()
        db.refresh(doc_record)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Failed to process document: {sanitized_msg}"
        )

@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all uploaded documents with metadata and processing status."""
    docs = db.query(Document).order_by(desc(Document.created_at)).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "file_hash": d.file_hash,
            "status": d.status,
            "page_count": d.page_count,
            "chunk_count": d.chunk_count,
            "extraction_method": d.extraction_method,
            "error_message": d.error_message,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]

@router.get("/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves metadata for a specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "file_hash": doc.file_hash,
        "status": doc.status,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "extraction_method": doc.extraction_method,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None
    }

def get_user_from_token_or_query(
    token: Optional[str] = Query(None, description="Session token for direct browser previews"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> User:
    auth_token = token
    if not auth_token and authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            auth_token = parts[1]

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required to view document file."
        )

    user = get_user_from_token(db, auth_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please sign in again."
        )
    return user


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_from_token_or_query)
):
    """
    Safely serves the uploaded document file for inline preview or download.
    Validates authentication token via query parameter (for browser new tabs) or Bearer header.
    Validates document existence, verifies the file exists on disk,
    and enforces strict upload-directory containment to prevent path traversal.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not doc.file_path or not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file does not exist on disk.")

    file_path_resolved = Path(doc.file_path).resolve()
    allowed_dir_resolved = settings.resolved_upload_dir.resolve()
    try:
        file_path_resolved.relative_to(allowed_dir_resolved)
    except ValueError:
        logger.error(f"Path traversal blocked: {doc.file_path} is outside {allowed_dir_resolved}")
        raise HTTPException(status_code=403, detail="Access denied: file is outside allowed directory.")

    media_type = "application/pdf" if doc.file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    disposition = f'inline; filename="{doc.filename}"'

    return FileResponse(
        path=str(file_path_resolved),
        media_type=media_type,
        filename=doc.filename,
        headers={"Content-Disposition": disposition}
    )

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns chunks for a document, including source page numbers.
    Enables source citation verification.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "total_chunks": len(chunks),
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "token_count": c.token_count,
                "content_preview": c.content[:150] + "..." if len(c.content) > 150 else c.content,
                "content": c.content
            }
            for c in chunks
        ]
    }

@router.post("/{document_id}/index")
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "editor"]))
):
    """
    Generates Cohere embeddings and persists chunks into ChromaDB for a document.
    Safe for re-indexing (purges old vectors before re-adding). Requires admin or editor role.
    """
    if not settings.is_cohere_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cohere API key is not configured. Please add COHERE_API_KEY in backend/.env."
        )

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")

        # Re-extract and re-chunk if file is still available on disk
        if doc.file_path and os.path.isfile(doc.file_path):
            indexed_count = reprocess_and_index_document(document_id, db)
        else:
            indexed_count = index_document_chunks(document_id, db)

        return {
            "document_id": document_id,
            "status": "indexed",
            "chunks_indexed": indexed_count,
            "message": f"Successfully indexed {indexed_count} chunks into ChromaDB."
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Indexing error for document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "editor"]))
):
    """
    Deletes a document, its stored file, associated chunks from SQLite,
    and purges all its vectors from ChromaDB. Requires admin or editor role.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 1. Purge vectors from ChromaDB
    try:
        vector_store.delete_document_vectors(document_id)
    except Exception as ve:
        logger.warning(f"Error purging vectors for doc {document_id}: {ve}")

    # 2. Remove file from disk if it exists
    if doc.file_path and os.path.isfile(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to remove file from disk: {e}")

    # 3. Delete from SQLite (cascades to chunks)
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' (ID: {document_id}) deleted successfully."}
