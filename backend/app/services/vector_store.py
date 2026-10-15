"""
ChromaDB vector store integration module.
Manages persistent embeddings collection, document vector indexing,
scoped document deletion, and cosine semantic retrieval.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from app.config import settings

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initializes persistent ChromaDB client and gets or creates the target collection.
        Allows custom persist_directory and collection_name for testing isolation.
        """
        if persist_directory:
            self.persist_directory = str(Path(persist_directory).resolve())
        else:
            self.persist_directory = str(settings.resolved_chroma_dir)

        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get or create collection configured with cosine distance
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ):
        """
        Adds or updates document chunk embeddings in ChromaDB.
        Avoids duplicates by using stable chunk_ids.
        """
        if not chunk_ids:
            return

        if not (len(chunk_ids) == len(embeddings) == len(documents) == len(metadatas)):
            raise ValueError("Mismatched counts for chunk_ids, embeddings, documents, and metadatas.")

        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def delete_document_vectors(self, document_id: int):
        """
        Deletes all vector embeddings associated with a given document_id.
        Ensures ChromaDB stays synchronized when documents are removed or re-indexed.
        """
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Purged ChromaDB vectors for document ID: {document_id}")
        except Exception as e:
            logger.warning(f"Error purging ChromaDB vectors for document ID {document_id}: {e}")

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[int] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB for the most semantically similar chunks.
        Optionally filters results by specific document_id and minimum similarity threshold.
        Returns formatted result objects with page numbers and similarity scores.
        """
        total_count = self.collection.count()
        if total_count == 0:
            return []

        # Cap top_k to actual available vectors
        n_results = min(top_k, total_count)
        where_filter = {"document_id": document_id} if document_id is not None else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted_matches: List[Dict[str, Any]] = []

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = distances[i] if i < len(distances) else 0.0
            # Cosine distance ranges from 0 (identical) to 2. Convert to similarity score [0, 1]
            similarity = max(0.0, 1.0 - dist)

            if min_similarity > 0.0 and similarity < min_similarity:
                continue

            formatted_matches.append({
                "chroma_id": chunk_id,
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "page_number": meta.get("page_number", 1),
                "chunk_index": meta.get("chunk_index", 0),
                "content": docs[i] if i < len(docs) else "",
                "distance": round(dist, 4),
                "similarity_score": round(similarity, 4)
            })

        return formatted_matches

    def count(self) -> int:
        """Returns the total number of vectors in the collection."""
        return self.collection.count()

# Default singleton instance for application use
vector_store = ChromaStore()
