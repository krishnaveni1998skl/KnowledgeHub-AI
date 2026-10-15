"""
Document indexing service.
Bridges SQLite document chunks with Cohere vector embeddings and persistent ChromaDB storage.
Rule 2: Stable vector IDs and metadata citations.
Rule 3: Avoids duplicate vectors, supports document re-indexing and error recovery.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models.schema import Document, DocumentChunk
from app.services.extractor import extract_text_from_pdf, extract_text_from_docx
from app.services.chunker import chunk_document
from app.services.rag import rag_service, CohereRAGService
from app.services.vector_store import vector_store, ChromaStore

logger = logging.getLogger(__name__)

def index_document_chunks(
    document_id: int,
    db: Session,
    rag: Optional[CohereRAGService] = None,
    store: Optional[ChromaStore] = None
) -> int:
    """
    Takes processed SQLite chunks for a document, generates Cohere embeddings,
    and persists them into ChromaDB with citation metadata.
    Avoids duplicate vectors by purging old vectors for this document first.
    Updates SQLite `chroma_id` on chunks and document status to 'indexed'.
    """
    rag_engine = rag or rag_service
    store_engine = store or vector_store

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document with ID {document_id} not found.")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )

    if not chunks:
        raise ValueError(f"Document ID {document_id} has no chunks to index.")

    # 1. Clear any existing vectors for this document to avoid duplicates
    store_engine.delete_document_vectors(document_id)

    # 2. Prepare payload
    chunk_texts = [c.content for c in chunks]
    chunk_ids = [f"doc_{document_id}_chunk_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "filename": doc.filename,
            "page_number": c.page_number,
            "chunk_index": c.chunk_index
        }
        for c in chunks
    ]

    # 3. Generate embeddings using Cohere search_document input_type
    logger.info(f"Generating Cohere embeddings for {len(chunks)} chunks of doc '{doc.filename}'...")
    embeddings = rag_engine.embed_documents(chunk_texts)

    if len(embeddings) != len(chunks):
        raise RuntimeError(f"Embedding count ({len(embeddings)}) does not match chunk count ({len(chunks)}).")

    # 4. Upsert into ChromaDB
    store_engine.upsert_chunks(
        chunk_ids=chunk_ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=metadatas
    )

    # 5. Update SQLite records with assigned chroma_ids
    for i, c in enumerate(chunks):
        c.chroma_id = chunk_ids[i]

    doc.status = "indexed"
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    logger.info(f"Successfully indexed document ID {document_id} ({len(chunks)} chunks) into ChromaDB.")
    return len(chunks)


def reprocess_and_index_document(
    document_id: int,
    db: Session,
    rag: Optional[CohereRAGService] = None,
    store: Optional[ChromaStore] = None
) -> int:
    """
    Re-extracts text, re-chunks, updates SQLite chunks, and re-indexes embeddings for a document.
    Ensures that updated chunking logic is applied to existing documents.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document with ID {document_id} not found.")

    if not doc.file_path or not os.path.isfile(doc.file_path):
        raise FileNotFoundError(f"File for document ID {document_id} not found at {doc.file_path}")

    extension = Path(doc.filename).suffix.lower()
    if extension == ".pdf":
        extraction = extract_text_from_pdf(doc.file_path)
    elif extension == ".docx":
        extraction = extract_text_from_docx(doc.file_path)
    else:
        raise ValueError(f"Unsupported file extension '{extension}' for document ID {document_id}.")

    pages = extraction.get("pages", [])
    chunks = chunk_document(
        pages,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )

    if not chunks:
        raise ValueError(f"No text extracted for document ID {document_id} during re-processing.")

    # Remove existing SQLite chunks for this document
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.commit()

    # Insert freshly chunked records
    for c in chunks:
        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=c["chunk_index"],
            page_number=c["page_number"],
            content=c["content"],
            token_count=c["token_count"]
        )
        db.add(db_chunk)

    doc.page_count = extraction.get("page_count", doc.page_count)
    doc.chunk_count = len(chunks)
    doc.extraction_method = extraction.get("extraction_method", doc.extraction_method)
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    logger.info(f"Re-processed document ID {document_id}: new chunk count is {len(chunks)}.")

    # Re-index vectors in ChromaDB
    return index_document_chunks(document_id, db, rag=rag, store=store)

