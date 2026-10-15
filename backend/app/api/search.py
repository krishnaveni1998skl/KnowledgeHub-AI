"""
Semantic Search & Grounded RAG Answer API router.
Provides endpoints for semantic vector retrieval and context-grounded AI answers.
Rule 4: Query embedding using search_query input_type and similarity scoring.
Rule 5: Grounded answers with source citations and conversation history in SQLite.
"""
import re
import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schema import ChatSession, ChatMessage, User
from app.services.vector_store import vector_store
from app.services.rag import rag_service, CohereServiceError
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Search & RAG"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="User search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of relevant chunks to return")
    document_id: Optional[int] = Field(default=None, description="Optional document ID to restrict search scope")

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="User question for RAG assistant")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of context chunks to retrieve for grounding")
    document_id: Optional[int] = Field(default=None, description="Optional document ID filter")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    language: Optional[str] = Field(default="en", description="Target response language: 'en', 'ta', or 'hi'")

@router.post("/search")
def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Performs semantic vector search across indexed document chunks using Cohere embeddings.
    Returns matching chunks with document metadata, page numbers, and cosine similarity scores.
    """
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty."
        )

    if not rag_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cohere API key is not configured. Please add COHERE_API_KEY in backend/.env to use semantic search."
        )

    if vector_store.count() == 0:
        return {
            "query": clean_query,
            "total_matches": 0,
            "results": [],
            "message": "No documents have been indexed into the vector store yet."
        }

    try:
        # Generate query embedding with search_query input_type
        query_vector = rag_service.embed_query(clean_query)

        # Retrieve nearest neighbor chunks from ChromaDB
        matches = vector_store.query_similar(
            query_embedding=query_vector,
            top_k=request.top_k,
            document_id=request.document_id,
            min_similarity=0.20
        )

        for i, m in enumerate(matches):
            logger.info(
                f"[Search Diagnostic] Match {i+1}/{len(matches)}: doc_id={m.get('document_id')}, "
                f"file='{m.get('filename')}', p.{m.get('page_number')}, idx={m.get('chunk_index')}, "
                f"similarity={m.get('similarity_score')}, distance={m.get('distance')}, "
                f"preview={repr(m.get('content', '')[:120])}"
            )

        return {
            "query": clean_query,
            "total_matches": len(matches),
            "results": matches
        }
    except CohereServiceError as cse:
        logger.error(f"Semantic search Cohere error [{cse.error_type}]: {cse.message}")
        http_status = cse.status_code if 400 <= cse.status_code < 600 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=http_status,
            detail=f"Semantic search failed: {cse.message}"
        )
    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )

@router.post("/rag/ask")
def ask_document_assistant(
    request: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieval-Augmented Generation (RAG) endpoint:
    1. Embeds user question.
    2. Retrieves top relevant chunks from ChromaDB.
    3. Prompts Cohere to generate an answer grounded strictly in retrieved context.
    4. Persists the Q&A exchange to SQLite chat history.
    5. Returns answer along with source document and page number citations in requested language.
    """
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    if not rag_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cohere API key is not configured. Please add COHERE_API_KEY in backend/.env to use the AI Assistant."
        )

    # 1. Semantic Retrieval
    context_chunks: List[Dict[str, Any]] = []
    if vector_store.count() > 0:
        try:
            query_vec = rag_service.embed_query(clean_question)
            context_chunks = vector_store.query_similar(
                query_embedding=query_vec,
                top_k=request.top_k,
                document_id=request.document_id,
                min_similarity=0.25
            )
            logger.info(f"[RAG Diagnostic] Retrieved {len(context_chunks)} chunks for question: {repr(clean_question[:80])}")
            for i, chunk in enumerate(context_chunks):
                logger.info(
                    f"[RAG Diagnostic] Chunk {i+1}/{len(context_chunks)}: doc_id={chunk.get('document_id')}, "
                    f"file='{chunk.get('filename')}', p.{chunk.get('page_number')}, idx={chunk.get('chunk_index')}, "
                    f"similarity={chunk.get('similarity_score')}, distance={chunk.get('distance')}, "
                    f"preview={repr(chunk.get('content', '')[:120])}"
                )
            # Deduplicate redundant/identical content chunks across duplicate document uploads
            unique_chunks = []
            seen_texts = set()
            for c in context_chunks:
                norm_text = re.sub(r'\s+', ' ', c.get("content", "").strip())
                if norm_text and norm_text in seen_texts:
                    continue
                if norm_text:
                    seen_texts.add(norm_text)
                unique_chunks.append(c)
            context_chunks = unique_chunks
        except Exception as e:
            logger.error(f"Retrieval error during RAG: {e}")

    # 2. Grounded Answer Generation in requested language
    target_lang = (request.language or "en").lower().strip()
    try:
        rag_output = rag_service.generate_grounded_answer(
            query=clean_question,
            context_chunks=context_chunks,
            language=target_lang
        )
    except CohereServiceError as cse:
        logger.error(f"Cohere RAG generation error [{cse.error_type}]: {cse.message}")
        http_status = cse.status_code if 400 <= cse.status_code < 600 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=http_status,
            detail=f"Cohere chat generation failed: {cse.message}"
        )
    except Exception as e:
        logger.error(f"Generation error during RAG: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )

    # 3. Store conversation in SQLite
    session_id = request.session_id or str(uuid.uuid4())
    session_record = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session_record:
        session_record = ChatSession(
            id=session_id,
            title=clean_question[:50] + ("..." if len(clean_question) > 50 else "")
        )
        db.add(session_record)
        db.commit()

    # Save User message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=clean_question,
        sources=None
    )
    # Save Assistant message with cited sources
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=rag_output["answer"],
        sources=json.dumps(rag_output["sources"])
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return {
        "session_id": session_id,
        "question": clean_question,
        "answer": rag_output.get("answer", ""),
        "sources": rag_output.get("sources", []),
        "chunks_used": rag_output.get("chunks_used", len(context_chunks))
    }
