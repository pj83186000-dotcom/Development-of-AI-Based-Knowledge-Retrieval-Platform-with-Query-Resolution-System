"""Repository layer for persisting and querying Documents, Chunks, and Embeddings.

Provides transactional persistence and helper methods for SQLite storage.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.database.models import (
    Chunk,
    Document,
    DocumentStatus,
    Embedding,
    FileType,
)


class DocumentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_document(self, doc: Document) -> None:
        """Insert a new Document record into SQLite."""
        query = """
            INSERT INTO documents (
                id, filename, file_type, file_size_bytes, file_hash, domain,
                chunk_count, status, upload_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                doc.id,
                doc.filename,
                doc.file_type.value,
                doc.file_size_bytes,
                doc.file_hash,
                doc.domain,
                doc.chunk_count,
                doc.status.value,
                doc.upload_timestamp.isoformat(),
            ),
        )
        self.conn.commit()

    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Fetch a document by its primary key ID."""
        cursor = self.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Document(
            id=row["id"],
            filename=row["filename"],
            file_type=FileType(row["file_type"]),
            file_size_bytes=row["file_size_bytes"],
            file_hash=row["file_hash"],
            domain=row["domain"],
            chunk_count=row["chunk_count"],
            status=DocumentStatus(row["status"]),
            upload_timestamp=row["upload_timestamp"],
        )

    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """Fetch a document by its SHA-256 hash to detect duplicates."""
        cursor = self.conn.execute(
            "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Document(
            id=row["id"],
            filename=row["filename"],
            file_type=FileType(row["file_type"]),
            file_size_bytes=row["file_size_bytes"],
            file_hash=row["file_hash"],
            domain=row["domain"],
            chunk_count=row["chunk_count"],
            status=DocumentStatus(row["status"]),
            upload_timestamp=row["upload_timestamp"],
        )

    def list_documents(self, domain: Optional[str] = None) -> List[Document]:
        """List all documents, optionally filtered by domain."""
        if domain:
            cursor = self.conn.execute(
                "SELECT * FROM documents WHERE domain = ? ORDER BY upload_timestamp DESC",
                (domain,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM documents ORDER BY upload_timestamp DESC"
            )
        rows = cursor.fetchall()
        return [
            Document(
                id=r["id"],
                filename=r["filename"],
                file_type=FileType(r["file_type"]),
                file_size_bytes=r["file_size_bytes"],
                file_hash=r["file_hash"],
                domain=r["domain"],
                chunk_count=r["chunk_count"],
                status=DocumentStatus(r["status"]),
                upload_timestamp=r["upload_timestamp"],
            )
            for r in rows
        ]

    def update_document_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunk_count: Optional[int] = None,
    ) -> None:
        """Update the processing status and chunk count of a document."""
        if chunk_count is not None:
            self.conn.execute(
                "UPDATE documents SET status = ?, chunk_count = ? WHERE id = ?",
                (status.value, chunk_count, doc_id),
            )
        else:
            self.conn.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                (status.value, doc_id),
            )
        self.conn.commit()


class ChunkRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_chunks(self, chunks: List[Chunk]) -> None:
        """Batch insert chunks for a document."""
        query = """
            INSERT INTO chunks (
                id, document_id, chunk_index, text, char_length, token_count,
                start_char, end_char, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        payload = [
            (
                c.id,
                c.document_id,
                c.chunk_index,
                c.text,
                c.char_length,
                c.token_count,
                c.start_char,
                c.end_char,
                json.dumps(c.metadata),
            )
            for c in chunks
        ]
        self.conn.executemany(query, payload)
        self.conn.commit()

    def get_chunks_by_document(self, doc_id: str) -> List[Chunk]:
        """Retrieve all chunks belonging to a document ordered by index."""
        cursor = self.conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
            (doc_id,),
        )
        rows = cursor.fetchall()
        return [
            Chunk(
                id=r["id"],
                document_id=r["document_id"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                char_length=r["char_length"],
                token_count=r["token_count"],
                start_char=r["start_char"],
                end_char=r["end_char"],
                metadata=json.loads(r["metadata_json"] or "{}"),
            )
            for r in rows
        ]

    def count_chunks(self, doc_id: Optional[str] = None) -> int:
        """Count total chunks, optionally for a specific document."""
        if doc_id:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,)
            )
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM chunks")
        return cursor.fetchone()[0]


class EmbeddingRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_embeddings(self, embeddings: List[Embedding]) -> None:
        """Batch insert embeddings with serialized 1536-byte vector BLOBs."""
        query = """
            INSERT INTO embeddings (
                id, chunk_id, model_name, dimension, vector_blob, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        payload = []
        for e in embeddings:
            # Ensure 1536-byte BLOB
            blob = e.vector_blob
            if blob is None:
                vec_arr = np.array(e.vector, dtype=np.float32)
                blob = vec_arr.tobytes()
            payload.append(
                (
                    e.id,
                    e.chunk_id,
                    e.model_name,
                    e.dimension,
                    blob,
                    e.created_at.isoformat(),
                )
            )
        self.conn.executemany(query, payload)
        self.conn.commit()

    def get_embedding_by_chunk_id(self, chunk_id: str) -> Optional[Embedding]:
        """Fetch embedding for a chunk, deserializing the float32 vector BLOB."""
        cursor = self.conn.execute(
            "SELECT * FROM embeddings WHERE chunk_id = ?", (chunk_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        blob = row["vector_blob"]
        vec_arr = np.frombuffer(blob, dtype=np.float32)
        return Embedding(
            id=row["id"],
            chunk_id=row["chunk_id"],
            model_name=row["model_name"],
            dimension=row["dimension"],
            vector=vec_arr.tolist(),
            vector_blob=blob,
            created_at=row["created_at"],
        )

    def count_embeddings(self) -> int:
        """Count total stored embeddings."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM embeddings")
        return cursor.fetchone()[0]

