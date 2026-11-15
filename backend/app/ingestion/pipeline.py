"""Knowledge base ingestion pipeline orchestrator.

Coordinates validation, extraction, cleaning, chunking, embedding generation,
and SQLite persistence in a single coherent workflow.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import sqlite3

from backend.app.database.connection import get_connection, init_db
from backend.app.database.models import Document, DocumentStatus, FileType
from backend.app.database.repository import (
    ChunkRepository,
    DocumentRepository,
    EmbeddingRepository,
)
from backend.app.ingestion.chunker import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    chunk_text,
)
from backend.app.ingestion.cleaner import clean_text
from backend.app.ingestion.embedder import generate_embeddings
from backend.app.ingestion.extractors import extract_document
from backend.app.ingestion.validators import (
    compute_sha256,
    generate_document_id,
    validate_file_format,
    validate_file_size,
)


@dataclass
class IngestionResult:
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    domain: str
    extracted_char_count: int
    chunk_count: int
    embedding_count: int
    status: str
    message: str
    is_duplicate: bool = False


class IngestionPipeline:
    def __init__(
        self,
        db_path: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ):
        self.db_path = db_path
        self._shared_conn = conn
        if conn is None:
            init_db(db_path)

    def _get_active_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        return get_connection(self.db_path)

    def process_file(
        self,
        filename: str,
        file_bytes: bytes,
        domain: str = "general",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> IngestionResult:
        """Execute end-to-end ingestion pipeline on uploaded document bytes.
        
        Args:
            filename: Original file name with extension.
            file_bytes: Raw binary content of the file.
            domain: Target domain classification (default 'general').
            chunk_size: Text chunk length in characters.
            chunk_overlap: Sliding window overlap in characters.
            
        Returns:
            IngestionResult summary of the completed ingestion.
            
        Raises:
            ValueError: On validation failure, empty file, or unsupported format.
        """
        # 1. Validation
        file_type = validate_file_format(filename)
        file_size = validate_file_size(file_bytes)
        file_hash = compute_sha256(file_bytes)

        conn = self._get_active_connection()
        should_close = (self._shared_conn is None)
        try:
            doc_repo = DocumentRepository(conn)
            chunk_repo = ChunkRepository(conn)
            emb_repo = EmbeddingRepository(conn)

            # 2. Check for duplicate upload
            existing_doc = doc_repo.get_document_by_hash(file_hash)
            if existing_doc:
                return IngestionResult(
                    document_id=existing_doc.id,
                    filename=existing_doc.filename,
                    file_type=existing_doc.file_type.value,
                    file_size_bytes=existing_doc.file_size_bytes,
                    file_hash=existing_doc.file_hash,
                    domain=existing_doc.domain,
                    extracted_char_count=0,
                    chunk_count=existing_doc.chunk_count,
                    embedding_count=existing_doc.chunk_count,
                    status=existing_doc.status.value,
                    message=f"Duplicate document detected. File already ingested as document ID '{existing_doc.id}'.",
                    is_duplicate=True,
                )

            # 3. Document Extraction
            raw_text, extract_meta = extract_document(file_bytes, file_type)

            # 4. Text Cleaning and Normalization
            cleaned = clean_text(raw_text)
            if not cleaned:
                raise ValueError("Extracted text was empty after cleaning and normalization.")

            # 5. Document Model Registration
            doc_id = generate_document_id()
            doc = Document(
                id=doc_id,
                filename=filename,
                file_type=file_type,
                file_size_bytes=file_size,
                file_hash=file_hash,
                domain=domain,
                chunk_count=0,
                status=DocumentStatus.PENDING,
            )

            # 6. Text Chunking
            chunks = chunk_text(
                cleaned_text=cleaned,
                document_id=doc_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                base_metadata=extract_meta,
            )
            if not chunks:
                raise ValueError("No valid chunks could be generated from document text.")

            # 7. Embedding Generation (384 dimensions, 1536-byte BLOBs)
            embeddings = generate_embeddings(chunks)

            # 8. Persistent Relational Storage (Transactional)
            doc.chunk_count = len(chunks)
            doc.status = DocumentStatus.PROCESSED
            doc_repo.insert_document(doc)
            chunk_repo.insert_chunks(chunks)
            emb_repo.insert_embeddings(embeddings)

            return IngestionResult(
                document_id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type.value,
                file_size_bytes=doc.file_size_bytes,
                file_hash=doc.file_hash,
                domain=doc.domain,
                extracted_char_count=len(cleaned),
                chunk_count=len(chunks),
                embedding_count=len(embeddings),
                status=doc.status.value,
                message=f"Successfully ingested {filename} into {len(chunks)} chunks with 384-dimensional embeddings.",
                is_duplicate=False,
            )
        finally:
            if should_close:
                conn.close()
