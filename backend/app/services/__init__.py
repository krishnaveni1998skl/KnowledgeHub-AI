# Modular Document & RAG Pipeline Services
from app.services.extractor import extract_text_from_pdf, extract_text_from_docx
from app.services.chunker import clean_text, chunk_document
from app.services.ocr import is_tesseract_available, ocr_image
from app.services.vector_store import vector_store, ChromaStore
from app.services.rag import rag_service, CohereRAGService
from app.services.indexer import index_document_chunks

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_docx",
    "clean_text",
    "chunk_document",
    "is_tesseract_available",
    "ocr_image",
    "vector_store",
    "ChromaStore",
    "rag_service",
    "CohereRAGService",
    "index_document_chunks",
]
