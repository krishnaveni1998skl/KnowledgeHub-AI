"""
Automated Test Suite for Phase 4: ChromaDB Vector Storage & Cohere RAG Service.
Mocks Cohere API calls to avoid requiring a real key or incurring network calls.
Uses isolated temporary ChromaDB directories for test safety.
"""
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import cohere

from app.main import app
from app.database import SessionLocal
from app.models.schema import Document, DocumentChunk, ChatSession, ChatMessage
from app.services.vector_store import ChromaStore, vector_store
from app.services.rag import CohereRAGService, rag_service, CohereServiceError, deduplicate_sources, extract_actual_sources
from app.services.indexer import index_document_chunks

@pytest.fixture
def temp_chroma_store():
    """Provides an isolated ChromaStore in a temporary directory."""
    temp_dir = tempfile.mkdtemp()
    store = ChromaStore(persist_directory=temp_dir, collection_name="test_collection")
    yield store
    shutil.rmtree(temp_dir, ignore_errors=True)

# ==========================================
# 1. Cohere Configuration & Missing Key Tests
# ==========================================

def test_cohere_missing_key_behavior():
    """Verify CohereRAGService handles missing API key safely without crashing."""
    service = CohereRAGService(api_key="")
    assert service.is_configured is False
    with pytest.raises(RuntimeError) as exc_info:
        service.embed_query("test query")
    assert "Cohere API key is not configured" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info:
        service.embed_documents(["chunk 1", "chunk 2"])
    assert "Cohere API key is not configured" in str(exc_info.value)

# ==========================================
# 2. ChromaDB Storage, Upsert, Query & Deletion
# ==========================================

def test_chromadb_upsert_query_and_delete(temp_chroma_store):
    """Verify ChromaDB stores embeddings with metadata and supports scoped deletion."""
    store = temp_chroma_store

    chunk_ids = ["doc_1_chunk_0", "doc_1_chunk_1", "doc_2_chunk_0"]
    embeddings = [
        [0.1, 0.2, 0.3, 0.4],
        [0.2, 0.3, 0.4, 0.5],
        [0.9, 0.8, 0.7, 0.6]
    ]
    documents = [
        "KnowledgeHub company policy section 1",
        "KnowledgeHub compliance guidelines section 2",
        "Operations playbook section 1"
    ]
    metadatas = [
        {"document_id": 1, "filename": "policy.pdf", "page_number": 1, "chunk_index": 0},
        {"document_id": 1, "filename": "policy.pdf", "page_number": 2, "chunk_index": 1},
        {"document_id": 2, "filename": "ops.docx", "page_number": 1, "chunk_index": 0}
    ]

    # 1. Upsert
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)
    assert store.count() == 3

    # 2. Query nearest neighbor to vector similar to doc 1
    results = store.query_similar(query_embedding=[0.12, 0.22, 0.31, 0.41], top_k=2)
    assert len(results) == 2
    assert results[0]["chroma_id"] == "doc_1_chunk_0"
    assert results[0]["filename"] == "policy.pdf"
    assert results[0]["page_number"] == 1
    assert results[0]["similarity_score"] > 0.9

    # 3. Query with document_id filter
    filtered_results = store.query_similar(query_embedding=[0.1, 0.2, 0.3, 0.4], top_k=5, document_id=2)
    assert len(filtered_results) == 1
    assert filtered_results[0]["document_id"] == 2
    assert filtered_results[0]["filename"] == "ops.docx"

    # 4. Scoped document vector deletion
    store.delete_document_vectors(document_id=1)
    assert store.count() == 1
    remaining = store.query_similar(query_embedding=[0.5, 0.5, 0.5, 0.5], top_k=5)
    assert len(remaining) == 1
    assert remaining[0]["document_id"] == 2

def test_duplicate_indexing_prevention(temp_chroma_store):
    """Verify upserting the same document chunks twice does not duplicate vectors."""
    store = temp_chroma_store

    chunk_ids = ["doc_5_chunk_0", "doc_5_chunk_1"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    documents = ["Text 1", "Text 2"]
    metadatas = [
        {"document_id": 5, "filename": "doc.pdf", "page_number": 1, "chunk_index": 0},
        {"document_id": 5, "filename": "doc.pdf", "page_number": 1, "chunk_index": 1}
    ]

    # Index first time
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)
    assert store.count() == 2

    # Re-index same chunk IDs
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)
    assert store.count() == 2  # Total must not double!

# ==========================================
# 3. SQLite & ChromaDB Indexing Synchronization
# ==========================================

def test_index_document_chunks_service(temp_chroma_store):
    """Verify index_document_chunks creates embeddings, saves to ChromaDB, and links chroma_id in SQLite."""
    db = SessionLocal()
    try:
        # Create a test document with chunks
        doc = Document(
            filename="test_sync.pdf",
            file_type="pdf",
            file_size=1024,
            file_path="mock/path.pdf",
            status="chunked",
            page_count=2,
            chunk_count=2
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        c1 = DocumentChunk(document_id=doc.id, chunk_index=0, page_number=1, content="Corporate overview", token_count=10)
        c2 = DocumentChunk(document_id=doc.id, chunk_index=1, page_number=2, content="Financial policies", token_count=12)
        db.add(c1)
        db.add(c2)
        db.commit()

        # Mock Cohere embedding service
        mock_rag = MagicMock(spec=CohereRAGService)
        mock_rag.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        # Run indexing service
        indexed_count = index_document_chunks(doc.id, db, rag=mock_rag, store=temp_chroma_store)
        assert indexed_count == 2

        # Check SQLite updates
        db.refresh(doc)
        assert doc.status == "indexed"
        db.refresh(c1)
        db.refresh(c2)
        assert c1.chroma_id == f"doc_{doc.id}_chunk_0"
        assert c2.chroma_id == f"doc_{doc.id}_chunk_1"

        # Check ChromaDB vectors
        assert temp_chroma_store.count() == 2

        # Clean up test doc
        db.delete(doc)
        db.commit()
    finally:
        db.close()

# ==========================================
# 4. Semantic Search & Grounded RAG API Tests
# ==========================================

def test_semantic_search_api_missing_key():
    """Verify search returns clear 400 error when Cohere is not configured."""
    with patch.object(rag_service, "api_key", ""):
        with TestClient(app) as client:
            resp = client.post("/api/search", json={"query": "test query", "top_k": 3})
            assert resp.status_code == 400
            assert "Cohere API key is not configured" in resp.json()["detail"]

def test_semantic_search_api_with_mock():
    """Verify /api/search returns matching chunks with page citation and similarity score."""
    mock_vector = [0.1, 0.2, 0.3]
    mock_matches = [
        {
            "chroma_id": "doc_10_chunk_0",
            "document_id": 10,
            "filename": "security_audit.pdf",
            "page_number": 3,
            "chunk_index": 0,
            "content": "All databases are encrypted at rest with AES-256.",
            "distance": 0.05,
            "similarity_score": 0.95
        }
    ]

    with patch.object(rag_service, "api_key", "mock_test_key"), \
         patch.object(rag_service, "embed_query", return_value=mock_vector), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=mock_matches):

        with TestClient(app) as client:
            resp = client.post("/api/search", json={"query": "database encryption", "top_k": 5})
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "database encryption"
            assert data["total_matches"] == 1
            match = data["results"][0]
            assert match["filename"] == "security_audit.pdf"
            assert match["page_number"] == 3
            assert match["similarity_score"] == 0.95

def test_grounded_rag_ask_api_with_mock():
    """Verify /api/rag/ask retrieves context, generates grounded answer, and saves session."""
    mock_chunks = [
        {
            "chroma_id": "doc_11_chunk_0",
            "document_id": 11,
            "filename": "employee_handbook.pdf",
            "page_number": 4,
            "chunk_index": 0,
            "content": "Standard annual leave entitlement is 25 days per calendar year."
        }
    ]
    mock_rag_response = {
        "answer": "According to the Employee Handbook (Page 4), standard annual leave entitlement is 25 days per calendar year.",
        "sources": [
            {"document_id": 11, "filename": "employee_handbook.pdf", "page_number": 4}
        ],
        "chunks_used": 1
    }

    with patch.object(rag_service, "api_key", "mock_test_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1]*5), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=mock_chunks), \
         patch.object(rag_service, "generate_grounded_answer", return_value=mock_rag_response):

        with TestClient(app) as client:
            resp = client.post("/api/rag/ask", json={
                "question": "How many days of annual leave do employees receive?",
                "top_k": 3
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "25 days per calendar year" in data["answer"]
            assert len(data["sources"]) == 1
            assert data["sources"][0]["filename"] == "employee_handbook.pdf"
            assert data["sources"][0]["page_number"] == 4
            assert "session_id" in data

def test_delete_document_purges_chroma_vectors():
    """Verify DELETE /api/documents/{id} invokes ChromaStore vector purge."""
    db = SessionLocal()
    try:
        doc = Document(
            filename="to_delete.pdf",
            file_type="pdf",
            file_size=512,
            file_path="mock/path.pdf",
            status="indexed"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        target_id = doc.id
    finally:
        db.close()

    with patch.object(vector_store, "delete_document_vectors") as mock_purge:
        with TestClient(app) as client:
            resp = client.delete(f"/api/documents/{target_id}")
            assert resp.status_code == 200
            mock_purge.assert_called_once_with(target_id)

# ==========================================
# 5. Cohere Error Categorization & Exception Safety Tests
# ==========================================

def test_cohere_chat_not_found_model_exception_handling():
    """Verify 404 ModelNotFoundError is cleanly parsed without raw headers dump."""
    service = CohereRAGService(api_key="mock_key", chat_model="command-r")
    mock_client = MagicMock()
    mock_client.chat.side_effect = cohere.NotFoundError(
        body={"message": "model 'command-r' was removed on September 15, 2025", "id": "req-999"},
        headers={"x-endpoint-request-id": "req-999", "content-type": "application/json"}
    )

    with patch.object(service, "get_client", return_value=mock_client):
        with pytest.raises(CohereServiceError) as exc_info:
            service.generate_grounded_answer(
                query="Hello",
                context_chunks=[{"filename": "doc.pdf", "page_number": 1, "document_id": 1, "content": "text"}]
            )

        err = exc_info.value
        assert err.status_code == 404
        assert err.error_type == "ModelNotFoundError"
        assert err.request_id == "req-999"
        assert "command-r" in err.message
        assert "headers:" not in err.message

def test_cohere_chat_auth_exception_handling():
    """Verify 401 AuthenticationError is cleanly parsed without raw headers dump."""
    service = CohereRAGService(api_key="mock_invalid_key")
    mock_client = MagicMock()
    mock_client.chat.side_effect = cohere.UnauthorizedError(
        body={"message": "invalid api token"},
        headers={"x-endpoint-request-id": "req-401"}
    )

    with patch.object(service, "get_client", return_value=mock_client):
        with pytest.raises(CohereServiceError) as exc_info:
            service.generate_grounded_answer(
                query="Hello",
                context_chunks=[{"filename": "doc.pdf", "page_number": 1, "document_id": 1, "content": "text"}]
            )

        err = exc_info.value
        assert err.status_code == 401
        assert err.error_type == "AuthenticationError"
        assert "COHERE_API_KEY" in err.message
        assert "headers:" not in err.message

def test_cohere_chat_rate_limit_exception_handling():
    """Verify 429 RateLimitError is cleanly parsed without raw headers dump."""
    service = CohereRAGService(api_key="mock_key")
    mock_client = MagicMock()
    mock_client.chat.side_effect = cohere.TooManyRequestsError(
        body={"message": "You have exceeded your trial rate limit of 20 requests per minute"},
        headers={"x-endpoint-request-id": "req-429"}
    )

    with patch.object(service, "get_client", return_value=mock_client):
        with pytest.raises(CohereServiceError) as exc_info:
            service.generate_grounded_answer(
                query="Hello",
                context_chunks=[{"filename": "doc.pdf", "page_number": 1, "document_id": 1, "content": "text"}]
            )

        err = exc_info.value
        assert err.status_code == 429
        assert err.error_type == "RateLimitError"
        assert "rate limit or quota exceeded" in err.message
        assert "headers:" not in err.message

def test_grounded_rag_ask_api_handles_cohere_model_not_found():
    """Verify /api/rag/ask maps ModelNotFoundError to clean 404 response without headers dump."""
    mock_chunks = [{"chroma_id": "c1", "document_id": 1, "filename": "doc.pdf", "page_number": 1, "chunk_index": 0, "content": "text"}]

    with patch.object(rag_service, "api_key", "mock_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1]*5), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=mock_chunks), \
         patch.object(rag_service, "generate_grounded_answer", side_effect=CohereServiceError(
             message="The configured Cohere model is not found or is no longer supported. Detail: model 'command-r' was removed on September 15, 2025. [Request ID: req-123]",
             status_code=404,
             error_type="ModelNotFoundError",
             request_id="req-123"
         )):

        with TestClient(app) as client:
            resp = client.post("/api/rag/ask", json={"question": "Test question", "top_k": 3})
            assert resp.status_code == 404
            data = resp.json()
            assert "The configured Cohere model is not found" in data["detail"]
            assert "headers:" not in data["detail"]

# ==========================================
# 6. Tabular / Student Report RAG Grounding Tests (Mocked)
# ==========================================

STUDENT_REPORT_CHUNK = {
    "chroma_id": "doc_99_chunk_0",
    "document_id": 99,
    "filename": "sample_student_report.pdf",
    "page_number": 1,
    "chunk_index": 0,
    "content": (
        "Student Report\n"
        "Student ID\nStudent Name\nDepartment\nAcademic Year\nStatus\n"
        "ST001\nRahul Kumar\nComputer Science\nIII Year\nActive\n"
        "ST002\nPriya Sharma\nInformation Technology\nII Year\nActive\n"
        "ST003\nArun Kumar\nMechanical Engineering\nIV Year\nInactive\n"
        "ST004\nDivya Raj\nElectronics and Communication\nIII Year\nActive\n"
        "ST005\nKarthik S\nCivil Engineering\nII Year\nActive"
    ),
    "distance": 0.15,
    "similarity_score": 0.85
}

def test_rag_student_report_rahul_kumar_department():
    """Verify RAG answers Rahul Kumar's department is Computer Science with page citation."""
    mock_rag_response = {
        "answer": "Rahul Kumar's department is Computer Science. [sample_student_report.pdf (Page 1)]",
        "sources": [{"document_id": 99, "filename": "sample_student_report.pdf", "page_number": 1}],
        "chunks_used": 1
    }

    with patch.object(rag_service, "api_key", "mock_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1]*5), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=[STUDENT_REPORT_CHUNK]), \
         patch.object(rag_service, "generate_grounded_answer", return_value=mock_rag_response):

        with TestClient(app) as client:
            resp = client.post("/api/rag/ask", json={
                "question": "What is Rahul Kumar's department?",
                "top_k": 5
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "Computer Science" in data["answer"]
            assert len(data["sources"]) == 1
            assert data["sources"][0]["filename"] == "sample_student_report.pdf"
            assert data["sources"][0]["page_number"] == 1

def test_rag_student_report_priya_sharma_academic_year():
    """Verify RAG answers Priya Sharma's academic year is II Year with page citation."""
    mock_rag_response = {
        "answer": "Priya Sharma's academic year is II Year. [sample_student_report.pdf (Page 1)]",
        "sources": [{"document_id": 99, "filename": "sample_student_report.pdf", "page_number": 1}],
        "chunks_used": 1
    }

    with patch.object(rag_service, "api_key", "mock_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1]*5), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=[STUDENT_REPORT_CHUNK]), \
         patch.object(rag_service, "generate_grounded_answer", return_value=mock_rag_response):

        with TestClient(app) as client:
            resp = client.post("/api/rag/ask", json={
                "question": "What is Priya Sharma's academic year?",
                "top_k": 5
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "II Year" in data["answer"]
            assert len(data["sources"]) == 1
            assert data["sources"][0]["filename"] == "sample_student_report.pdf"
            assert data["sources"][0]["page_number"] == 1

def test_rag_student_report_arun_kumar_status():
    """Verify RAG answers Arun Kumar's status is Inactive with page citation."""
    mock_rag_response = {
        "answer": "The status of Arun Kumar is Inactive. [sample_student_report.pdf (Page 1)]",
        "sources": [{"document_id": 99, "filename": "sample_student_report.pdf", "page_number": 1}],
        "chunks_used": 1
    }

    with patch.object(rag_service, "api_key", "mock_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1]*5), \
         patch.object(vector_store, "count", return_value=1), \
         patch.object(vector_store, "query_similar", return_value=[STUDENT_REPORT_CHUNK]), \
         patch.object(rag_service, "generate_grounded_answer", return_value=mock_rag_response):

        with TestClient(app) as client:
            resp = client.post("/api/rag/ask", json={
                "question": "What is the status of Arun Kumar?",
                "top_k": 5
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "Inactive" in data["answer"]
            assert len(data["sources"]) == 1
            assert data["sources"][0]["filename"] == "sample_student_report.pdf"
            assert data["sources"][0]["page_number"] == 1

def test_chunker_prevents_character_by_character_tail_sliding():
    """Verify chunker produces bounded chunks without micro-sliding trailing artifacts."""
    from app.services.chunker import split_text_with_overlap
    sample_text = (
        "Student Report\n"
        "ST001 Rahul Kumar Computer Science III Year Active\n"
        "ST002 Priya Sharma Information Technology II Year Active\n"
        "ST003 Arun Kumar Mechanical Engineering IV Year Inactive\n"
        "ST004 Divya Raj Electronics and Communication III Year Active\n"
        "ST005 Karthik S Civil Engineering II Year Active\n"
        "Sample questions for testing:\n"
        "1. What is Rahul Kumar's department?\n"
        "2. Which student is in the Mechanical Engineering department?\n"
        "3. What is Priya Sharma's academic year?\n"
        "4. Which students are active?\n"
        "5. What is the status of Arun Kumar?"
    )
    chunks = split_text_with_overlap(sample_text, chunk_size=300, chunk_overlap=50)
    # Must terminate cleanly and not produce 100+ sliding fragments
    assert len(chunks) <= 4
    for c in chunks:
        # No micro-fragments like single words or questions
        assert len(c) > 30

def test_generate_grounded_answer_passes_structured_system_prompt():
    """Verify generate_grounded_answer formats structured context and guides the model on tables."""
    service = CohereRAGService(api_key="mock_key")
    mock_client = MagicMock()
    mock_chat_result = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Rahul Kumar's department is Computer Science."
    mock_chat_result.message.content = [mock_part]
    mock_client.chat.return_value = mock_chat_result

    with patch.object(service, "get_client", return_value=mock_client):
        res = service.generate_grounded_answer(
            query="What is Rahul Kumar's department?",
            context_chunks=[STUDENT_REPORT_CHUNK]
        )
        assert res["answer"] == "Rahul Kumar's department is Computer Science."
        assert len(res["sources"]) == 1
        assert res["sources"][0]["filename"] == "sample_student_report.pdf"

        call_args = mock_client.chat.call_args[1]
        messages = call_args["messages"]
        system_msg = next(m["content"] for m in messages if m["role"] == "system")
        assert "structured records" in system_msg
        assert "UNTRUSTED" in system_msg
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "sample_student_report.pdf" in user_msg
        assert "Rahul Kumar" in user_msg

# ==========================================
# 7. Document Source Isolation & Citation Accuracy Tests
# ==========================================

def test_document_isolation_with_document_id(temp_chroma_store):
    """Verify semantic retrieval strictly isolates results when document_id is provided."""
    store = temp_chroma_store
    chunk_ids = ["doc_1_chunk_0", "doc_2_chunk_0"]
    embeddings = [[0.1, 0.2], [0.1, 0.2]]
    documents = ["Student Rahul Kumar CS", "HR Handbook Vacation Policy"]
    metadatas = [
        {"document_id": 1, "filename": "sample_student_report.pdf", "page_number": 1, "chunk_index": 0},
        {"document_id": 2, "filename": "hr_handbook.pdf", "page_number": 1, "chunk_index": 0}
    ]
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)

    # Scoped query to document 1 only
    results = store.query_similar(query_embedding=[0.1, 0.2], top_k=5, document_id=1)
    assert len(results) == 1
    assert results[0]["document_id"] == 1
    assert results[0]["filename"] == "sample_student_report.pdf"

    # Scoped query to document 2 only
    results2 = store.query_similar(query_embedding=[0.1, 0.2], top_k=5, document_id=2)
    assert len(results2) == 1
    assert results2[0]["document_id"] == 2
    assert results2[0]["filename"] == "hr_handbook.pdf"

def test_unrelated_document_citation_suppression():
    """Verify that unrelated retrieved chunks (e.g. hr_handbook.pdf) are not cited when question is about student report."""
    service = CohereRAGService(api_key="mock_key")
    mock_client = MagicMock()
    mock_chat_result = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Rahul Kumar's department is Computer Science. [Source 1: sample_student_report.pdf (Page 1)]"
    mock_chat_result.message.content = [mock_part]
    mock_client.chat.return_value = mock_chat_result

    mixed_context = [
        {
            "document_id": 20,
            "filename": "sample_student_report.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "content": "ST001 Rahul Kumar Computer Science III Year Active"
        },
        {
            "document_id": 37,
            "filename": "hr_handbook.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "content": "All employees are entitled to standard corporate holidays."
        }
    ]

    with patch.object(service, "get_client", return_value=mock_client):
        res = service.generate_grounded_answer(
            query="What is Rahul Kumar's department?",
            context_chunks=mixed_context
        )
        assert res["answer"] == "Rahul Kumar's department is Computer Science. [Source 1: sample_student_report.pdf (Page 1)]"
        # Only the cited document should appear in sources, hr_handbook.pdf must be excluded
        assert len(res["sources"]) == 1
        assert res["sources"][0]["filename"] == "sample_student_report.pdf"
        assert res["sources"][0]["document_id"] == 20
        assert not any(s["filename"] == "hr_handbook.pdf" for s in res["sources"])

def test_unfound_answer_sources_are_empty():
    """Verify that when the assistant cannot find the answer, sources is an empty list."""
    service = CohereRAGService(api_key="mock_key")
    mock_client = MagicMock()
    mock_chat_result = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "I cannot find the answer to this question in the provided company documents."
    mock_chat_result.message.content = [mock_part]
    mock_client.chat.return_value = mock_chat_result

    context = [
        {
            "document_id": 20,
            "filename": "sample_student_report.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "content": "Some report content"
        }
    ]

    with patch.object(service, "get_client", return_value=mock_client):
        res = service.generate_grounded_answer(
            query="Who is the president of France?",
            context_chunks=context
        )
        assert "cannot find the answer" in res["answer"]
        # Sources must be empty when answer could not be found
        assert res["sources"] == []

def test_similarity_threshold_filters_out_low_scoring_chunks(temp_chroma_store):
    """Verify that min_similarity discards low-relevance chunks from retrieval."""
    store = temp_chroma_store
    chunk_ids = ["c_high", "c_low"]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    documents = ["High similarity text", "Low similarity unrelated text"]
    metadatas = [
        {"document_id": 1, "filename": "relevant.pdf", "page_number": 1, "chunk_index": 0},
        {"document_id": 2, "filename": "unrelated.pdf", "page_number": 1, "chunk_index": 0}
    ]
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)

    # Without threshold, returns both
    all_res = store.query_similar(query_embedding=[1.0, 0.0], top_k=5, min_similarity=0.0)
    assert len(all_res) == 2

    # With threshold 0.50, low similarity chunk is excluded
    filtered_res = store.query_similar(query_embedding=[1.0, 0.0], top_k=5, min_similarity=0.50)
    assert len(filtered_res) == 1
    assert filtered_res[0]["chroma_id"] == "c_high"
    assert filtered_res[0]["filename"] == "relevant.pdf"


# ==========================================
# 10. Citation Deduplication & Document Scoping Tests
# ==========================================

def test_citation_deduplication_same_doc_and_page():
    """Verify deduplicate_sources merges duplicate chunk citations from the same document & page."""
    sources = [
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 1},
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 1},
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 2},
    ]
    deduped = deduplicate_sources(sources)
    assert len(deduped) == 2
    assert deduped[0]["page_number"] == 1
    assert deduped[1]["page_number"] == 2


def test_citation_deduplication_across_duplicate_uploads():
    """Verify that identical documents uploaded multiple times (different doc IDs) are deduplicated by filename + page."""
    sources = [
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 1},
        {"document_id": 35, "filename": "sample_student_report.pdf", "page_number": 1},
    ]
    deduped = deduplicate_sources(sources)
    # Must yield only 1 citation for sample_student_report.pdf (Page 1)
    assert len(deduped) == 1
    assert deduped[0]["filename"] == "sample_student_report.pdf"
    assert deduped[0]["page_number"] == 1


def test_extract_actual_sources_deduplicates_explicit_sources():
    """Verify extract_actual_sources deduplicates multiple [Source X] tags pointing to the same document/page."""
    context = [
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 1, "content": "Rahul Kumar CS"},
        {"document_id": 35, "filename": "sample_student_report.pdf", "page_number": 1, "content": "Rahul Kumar CS dup"},
    ]
    answer = "Rahul Kumar is in Computer Science according to [Source 1] and [Source 2]."
    sources = extract_actual_sources(answer, context)
    assert len(sources) == 1
    assert sources[0]["filename"] == "sample_student_report.pdf"
    assert sources[0]["page_number"] == 1


def test_document_scoping_isolation_in_vector_query(temp_chroma_store):
    """Verify querying with document_id strictly isolates results to that document only."""
    store = temp_chroma_store
    chunk_ids = ["doc20_c0", "doc48_c0"]
    embeddings = [[0.8, 0.2], [0.85, 0.25]]
    documents = [
        "ST001 Rahul Kumar Computer Science III Year Active in sample_student_report",
        "ST001 Rahul Kumar Computer Science III Year Active in Student_Report _1_"
    ]
    metadatas = [
        {"document_id": 20, "filename": "sample_student_report.pdf", "page_number": 1, "chunk_index": 0},
        {"document_id": 48, "filename": "Student_Report _1_.pdf", "page_number": 1, "chunk_index": 0}
    ]
    store.upsert_chunks(chunk_ids, embeddings, documents, metadatas)

    # 1. Querying without filter returns both (all documents)
    all_results = store.query_similar(query_embedding=[0.8, 0.2], top_k=5)
    assert len(all_results) == 2

    # 2. Querying with document_id=48 strictly isolates to Student_Report _1_.pdf
    scoped_48 = store.query_similar(query_embedding=[0.8, 0.2], top_k=5, document_id=48)
    assert len(scoped_48) == 1
    assert scoped_48[0]["document_id"] == 48
    assert scoped_48[0]["filename"] == "Student_Report _1_.pdf"

    # 3. Querying with document_id=20 strictly isolates to sample_student_report.pdf
    scoped_20 = store.query_similar(query_embedding=[0.8, 0.2], top_k=5, document_id=20)
    assert len(scoped_20) == 1
    assert scoped_20[0]["document_id"] == 20
    assert scoped_20[0]["filename"] == "sample_student_report.pdf"


def test_ask_api_document_id_scoping():
    """Verify POST /api/search/ask passes document_id filter down to vector_store and restricts context."""
    client = TestClient(app)

    mock_chunks = [
        {
            "chroma_id": "doc_48_c0",
            "document_id": 48,
            "filename": "Student_Report _1_.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "content": "Rahul Kumar Computer Science III Year Active",
            "similarity_score": 0.95
        }
    ]

    with patch.object(rag_service, "api_key", "mock_test_key"), \
         patch.object(rag_service, "embed_query", return_value=[0.1, 0.2, 0.3]), \
         patch.object(vector_store, "count", return_value=5), \
         patch.object(vector_store, "query_similar", return_value=mock_chunks) as mock_query, \
         patch.object(rag_service, "generate_grounded_answer") as mock_generate:

        mock_generate.return_value = {
            "answer": "Rahul Kumar is in Computer Science [Source 1].",
            "sources": [{"document_id": 48, "filename": "Student_Report _1_.pdf", "page_number": 1}],
            "chunks_used": 1
        }

        resp = client.post("/api/rag/ask", json={
            "question": "What is Rahul Kumar's department?",
            "document_id": 48,
            "top_k": 3
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Rahul Kumar is in Computer Science [Source 1]."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["document_id"] == 48
        assert data["sources"][0]["filename"] == "Student_Report _1_.pdf"

        # Verify query_similar was called with document_id=48
        mock_query.assert_called_once()
        _, kwargs = mock_query.call_args
        assert kwargs.get("document_id") == 48


