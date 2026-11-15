"""Semantic search engine for Milestone 1.4 RAG retrieval.

Computes exact Cosine Similarity dot-product against stored 384-D chunk embeddings,
ranks candidate passages, applies configurable similarity thresholds, and manages Top-K context assembly.
"""

from dataclasses import dataclass, field
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.database.connection import get_connection
from backend.app.database.models import Query, QueryType, RetrievalResult
from backend.app.ingestion.embedder import get_embedding_model

DEFAULT_SIMILARITY_THRESHOLD = 0.35
MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    domain: str
    chunk_index: int
    text: str
    similarity_score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResultPayload:
    query: str
    query_id: str
    session_id: str
    total_indexed_chunks: int
    max_similarity_score: float
    similarity_threshold: float
    has_sufficient_context: bool
    status: str  # 'retrieved' | 'unavailable' | 'empty_corpus'
    retrieved_chunks: List[RetrievedChunk]
    top_1: Optional[RetrievedChunk] = None
    top_3: List[RetrievedChunk] = field(default_factory=list)
    top_5: List[RetrievedChunk] = field(default_factory=list)
    message: str = ""


class SemanticSearchEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _load_corpus_vectors(
        self, conn: sqlite3.Connection, domain: Optional[str] = None
    ):
        """Load indexed embeddings and metadata from SQLite.
        
        Returns:
            matrix: 2D numpy array of shape (M, 384) with float32 values.
            metadata_rows: List of dicts with chunk metadata.
        """
        sql = """
            SELECT 
                e.chunk_id,
                e.vector_blob,
                c.document_id,
                c.chunk_index,
                c.text,
                c.metadata_json,
                d.filename as document_name,
                d.domain
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.id
            JOIN documents d ON c.document_id = d.id
        """
        params = []
        if domain:
            sql += " WHERE d.domain = ?"
            params.append(domain)
        sql += " ORDER BY c.document_id, c.chunk_index ASC"

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        
        if not rows:
            return np.empty((0, 384), dtype=np.float32), []

        vector_list = []
        meta_list = []
        for r in rows:
            blob = r["vector_blob"]
            vec = np.frombuffer(blob, dtype=np.float32)
            vector_list.append(vec)
            meta_list.append(
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "document_name": r["document_name"],
                    "domain": r["domain"],
                    "chunk_index": r["chunk_index"],
                    "text": r["text"],
                    "metadata_json": r["metadata_json"],
                }
            )

        matrix = np.vstack(vector_list).astype(np.float32)
        return matrix, meta_list

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        domain: Optional[str] = None,
        session_id: Optional[str] = None,
        log_to_db: bool = True,
    ) -> SearchResultPayload:
        """Execute semantic search against the knowledge base.
        
        Args:
            query_text: Natural language user question.
            top_k: Number of candidate chunks to return (default: 5).
            similarity_threshold: Minimum cosine similarity score cutoff (default: 0.35).
            domain: Optional domain filter ('cloud_devops', 'healthcare').
            session_id: Session identifier for conversational audit logging.
            log_to_db: Whether to record query and retrieval results in SQLite tables.
            
        Returns:
            SearchResultPayload with ranked chunks and Top-1/3/5 context slices.
        """
        cleaned_query = (query_text or "").strip()
        if not cleaned_query:
            raise ValueError("Search query cannot be empty or whitespace.")

        q_id = f"qry_{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

        conn = get_connection(self.db_path)
        try:
            # 1. Load active corpus vectors
            matrix, meta_list = self._load_corpus_vectors(conn, domain=domain)
            total_chunks = len(meta_list)

            if total_chunks == 0:
                payload = SearchResultPayload(
                    query=cleaned_query,
                    query_id=q_id,
                    session_id=sess_id,
                    total_indexed_chunks=0,
                    max_similarity_score=-1.0,
                    similarity_threshold=similarity_threshold,
                    has_sufficient_context=False,
                    status="empty_corpus",
                    retrieved_chunks=[],
                    top_1=None,
                    top_3=[],
                    top_5=[],
                    message="No documents or embeddings found in the knowledge base.",
                )
                if log_to_db:
                    self._log_query(conn, payload)
                return payload

            # 2. Generate normalized 384-D query embedding
            model = get_embedding_model(MODEL_NAME)
            query_vec = model.encode(
                cleaned_query,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).astype(np.float32)

            if len(query_vec.shape) == 1:
                query_vec = np.expand_dims(query_vec, axis=0)

            # 3. Vectorized Dot-Product Cosine Similarity: S = Q · D^T
            # Both vectors are L2-normalized, so dot product is exact cosine similarity
            scores = np.dot(query_vec, matrix.T).flatten()

            # 4. Sort descending by similarity score
            sorted_indices = np.argsort(-scores)
            max_score = float(scores[sorted_indices[0]]) if len(sorted_indices) > 0 else -1.0

            # 5. Threshold Filtering
            has_sufficient = max_score >= similarity_threshold
            
            candidate_chunks: List[RetrievedChunk] = []
            rank = 1
            for idx in sorted_indices:
                score = float(scores[idx])
                if score < similarity_threshold:
                    # Do not include chunks that fail the threshold
                    break
                
                m = meta_list[idx]
                chunk_obj = RetrievedChunk(
                    chunk_id=m["chunk_id"],
                    document_id=m["document_id"],
                    document_name=m["document_name"],
                    domain=m["domain"],
                    chunk_index=m["chunk_index"],
                    text=m["text"],
                    similarity_score=round(score, 4),
                    rank=rank,
                )
                candidate_chunks.append(chunk_obj)
                rank += 1
                if rank > top_k:
                    break

            # 6. Slices for Top-1, Top-3, Top-5
            top_1 = candidate_chunks[0] if candidate_chunks else None
            top_3 = candidate_chunks[:3]
            top_5 = candidate_chunks[:5]

            status_str = "retrieved" if has_sufficient else "unavailable"
            if has_sufficient:
                msg = f"Retrieved {len(candidate_chunks)} relevant passage(s). Highest similarity score: {max_score:.4f}."
            else:
                msg = (
                    f"Information unavailable in knowledge base. "
                    f"Top similarity score ({max_score:.4f}) is below the required threshold of {similarity_threshold:.2f}."
                )

            payload = SearchResultPayload(
                query=cleaned_query,
                query_id=q_id,
                session_id=sess_id,
                total_indexed_chunks=total_chunks,
                max_similarity_score=round(max_score, 4),
                similarity_threshold=similarity_threshold,
                has_sufficient_context=has_sufficient,
                status=status_str,
                retrieved_chunks=candidate_chunks,
                top_1=top_1,
                top_3=top_3,
                top_5=top_5,
                message=msg,
            )

            # 7. Audit Logging in SQLite
            if log_to_db:
                self._log_query(conn, payload)

            return payload
        finally:
            conn.close()

    def _log_query(self, conn: sqlite3.Connection, payload: SearchResultPayload):
        """Record query and matched retrieval results in queries and retrieval_results tables."""
        try:
            # Insert Query record
            conn.execute(
                """
                INSERT INTO queries (id, session_id, raw_query_text, processed_query_text, query_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.query_id,
                    payload.session_id,
                    payload.query,
                    payload.query,
                    "factual" if payload.has_sufficient_context else "unavailable",
                ),
            )
            
            # Insert RetrievalResult records
            res_rows = []
            for c in payload.retrieved_chunks:
                res_rows.append(
                    (
                        f"res_{uuid.uuid4().hex[:12]}",
                        payload.query_id,
                        c.chunk_id,
                        c.document_id,
                        c.document_name,
                        c.text,
                        c.similarity_score,
                        c.rank,
                    )
                )
            if res_rows:
                conn.executemany(
                    """
                    INSERT INTO retrieval_results (
                        id, query_id, chunk_id, document_id, document_name, chunk_text, similarity_score, rank
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    res_rows,
                )
            conn.commit()
        except Exception:
            # Audit logging failure should not abort the retrieval response
            pass

