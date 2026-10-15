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

    # 2. Check session ownership & fetch recent history for follow-up questions
    session_id = request.session_id or str(uuid.uuid4())
    session_record = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session_record:
        session_record = ChatSession(
            id=session_id,
            user_id=current_user.id,
            title=clean_question[:50] + ("..." if len(clean_question) > 50 else "")
        )
        db.add(session_record)
        db.commit()
    elif session_record.user_id is not None and session_record.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: This conversation session belongs to another user."
        )

    # Fetch recent turns for conversational follow-up questions
    recent_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.id.desc()).limit(6).all()
    chat_history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]

    # 3. Grounded Answer Generation in requested language
    target_lang = (request.language or "en").lower().strip()
    try:
        rag_output = rag_service.generate_grounded_answer(
            query=clean_question,
            context_chunks=context_chunks,
            language=target_lang,
            chat_history=chat_history
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

    # 4. Save User & Assistant messages to session
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=clean_question,
        sources=None
    )
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


# ==========================================
# User-Specific Chat History & Isolation Endpoints
# ==========================================

@router.get("/rag/sessions")
def list_user_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns chat sessions belonging strictly to the authenticated user.
    Enforces conversation isolation across users.
    """
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "message_count": len(s.messages)
        }
        for s in sessions
    ]


@router.get("/rag/sessions/{session_id}")
def get_user_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full message history for a specific chat session.
    Enforces conversation isolation: raises 403 Forbidden if accessed by another non-admin user.
    """
    session_record = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session_record:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if session_record.user_id is not None and session_record.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view another user's conversation."
        )

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.id.asc()).all()

    return {
        "id": session_record.id,
        "title": session_record.title,
        "user_id": session_record.user_id,
        "created_at": session_record.created_at.isoformat() if session_record.created_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": json.loads(m.sources) if m.sources else [],
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }


@router.delete("/rag/sessions/{session_id}")
def delete_user_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a chat session and its associated messages.
    Enforces conversation isolation: raises 403 Forbidden if attempted by another non-admin user.
    """
    session_record = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session_record:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if session_record.user_id is not None and session_record.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot delete another user's conversation."
        )

    db.delete(session_record)
    db.commit()
    return {"message": "Chat session and conversation history deleted successfully."}


# ==========================================
# Dashboard Statistics Endpoint
# ==========================================

@router.get("/dashboard/stats")
def get_dashboard_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Provides real-time system and user-specific dashboard metrics.
    Enforces user isolation for conversation counts.
    """
    from app.models.schema import Document, DocumentChunk

    total_docs = db.query(Document).count()
    indexed_docs = db.query(Document).filter(Document.status == "indexed").count()
    failed_docs = db.query(Document).filter(Document.status == "failed").count()
    total_chunks = db.query(DocumentChunk).count()

    # User-specific metrics
    user_conversations = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).count()
    user_messages = db.query(ChatMessage).join(ChatSession).filter(ChatSession.user_id == current_user.id).count()

    vector_count = 0
    try:
        vector_count = vector_store.count()
    except Exception:
        pass

    return {
        "total_documents": total_docs,
        "indexed_documents": indexed_docs,
        "failed_documents": failed_docs,
        "total_chunks": total_chunks,
        "total_vectors": vector_count,
        "user_conversations": user_conversations,
        "user_messages": user_messages,
        "user_role": current_user.role,
        "user_email": current_user.email,
        "user_name": current_user.full_name,
        "cohere_configured": rag_service.is_configured,
        "status": "operational"
    }
