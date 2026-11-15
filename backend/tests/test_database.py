"""Unit tests for SQLite database schema, foreign keys, and repository operations."""

import sqlite3
import numpy as np
import pytest

from backend.app.database.connection import get_connection, init_db
from backend.app.database.models import (
    Chunk,
    Document,
    DocumentStatus,
    Embedding,
    FileType,
)
from backend.app.database.repository import (
    ChunkRepository,
    DocumentRepository,
    EmbeddingRepository,
)


@pytest.fixture
def in_memory_db(tmp_path):
    """Create an isolated test database in a temporary directory."""
    db_file = tmp_path / "test_db.sqlite"
    init_db(str(db_file))
    conn = get_connection(str(db_file))
    yield conn
    conn.close()


def test_schema_tables_exist(in_memory_db):
    cursor = in_memory_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {"documents", "chunks", "embeddings", "queries", "retrieval_results", "responses"}
    assert expected.issubset(tables)


def test_document_crud_and_duplicate_hash(in_memory_db):
    repo = DocumentRepository(in_memory_db)
    doc = Document(
        id="doc_db_test_01",
        filename="runbook.txt",
        file_type=FileType.TXT,
        file_size_bytes=512,
        file_hash="1" * 64,
        domain="cloud_devops",
        chunk_count=2,
        status=DocumentStatus.PROCESSED,
    )
    repo.insert_document(doc)
    
    # Query by ID
    fetched = repo.get_document_by_id("doc_db_test_01")
    assert fetched is not None
    assert fetched.filename == "runbook.txt"
    assert fetched.file_hash == "1" * 64
    
    # Query by Hash
    duplicate_match = repo.get_document_by_hash("1" * 64)
    assert duplicate_match is not None
    assert duplicate_match.id == "doc_db_test_01"
    
    # Non-existent hash
    assert repo.get_document_by_hash("0" * 64) is None


def test_chunk_persistence_and_ordering(in_memory_db):
    doc_repo = DocumentRepository(in_memory_db)
    chunk_repo = ChunkRepository(in_memory_db)
    
    doc = Document(
        id="doc_chunk_test",
        filename="protocol.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
        file_hash="2" * 64,
        domain="healthcare",
    )
    doc_repo.insert_document(doc)
    
    c1_text = "First passage of clinical protocol."
    c1 = Chunk(
        id="chk_01",
        document_id=doc.id,
        chunk_index=0,
        text=c1_text,
        char_length=len(c1_text),
        token_count=8,
        start_char=0,
        end_char=len(c1_text),
    )
    c2_text = "Second passage covering drug dosage."
    c2 = Chunk(
        id="chk_02",
        document_id=doc.id,
        chunk_index=1,
        text=c2_text,
        char_length=len(c2_text),
        token_count=8,
        start_char=len(c1_text),
        end_char=len(c1_text) + len(c2_text),
    )
    chunk_repo.insert_chunks([c1, c2])
    
    chunks = chunk_repo.get_chunks_by_document(doc.id)
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunk_repo.count_chunks(doc.id) == 2


def test_embedding_persistence_and_blob_constraint(in_memory_db):
    doc_repo = DocumentRepository(in_memory_db)
    chunk_repo = ChunkRepository(in_memory_db)
    emb_repo = EmbeddingRepository(in_memory_db)
    
    doc = Document(
        id="doc_emb_test",
        filename="specs.docx",
        file_type=FileType.DOCX,
        file_size_bytes=2048,
        file_hash="3" * 64,
    )
    doc_repo.insert_document(doc)
    
    chunk = Chunk(
        id="chk_emb_test",
        document_id=doc.id,
        chunk_index=0,
        text="Detailed CI/CD deployment specifications.",
        char_length=41,
        token_count=9,
        start_char=0,
        end_char=41,
    )
    chunk_repo.insert_chunks([chunk])
    
    vec = np.ones(384, dtype=np.float32)
    blob = vec.tobytes()
    assert len(blob) == 1536
    
    emb = Embedding(
        id="emb_01",
        chunk_id=chunk.id,
        dimension=384,
        vector=vec.tolist(),
        vector_blob=blob,
    )
    emb_repo.insert_embeddings([emb])
    
    fetched = emb_repo.get_embedding_by_chunk_id(chunk.id)
    assert fetched is not None
    assert fetched.dimension == 384
    assert len(fetched.vector_blob) == 1536


def test_foreign_key_enforcement(in_memory_db):
    chunk_repo = ChunkRepository(in_memory_db)
    # Attempting to insert chunk for non-existent document ID must fail
    orphan_chunk = Chunk(
        id="chk_orphan",
        document_id="doc_non_existent",
        chunk_index=0,
        text="Orphan chunk text snippet.",
        char_length=26,
        token_count=6,
        start_char=0,
        end_char=26,
    )
    with pytest.raises(sqlite3.IntegrityError):
        chunk_repo.insert_chunks([orphan_chunk])


def test_cascading_deletion(in_memory_db):
    doc_repo = DocumentRepository(in_memory_db)
    chunk_repo = ChunkRepository(in_memory_db)
    emb_repo = EmbeddingRepository(in_memory_db)
    
    doc = Document(
        id="doc_cascade",
        filename="cascade.txt",
        file_type=FileType.TXT,
        file_size_bytes=100,
        file_hash="4" * 64,
    )
    doc_repo.insert_document(doc)
    
    chunk = Chunk(
        id="chk_cascade",
        document_id=doc.id,
        chunk_index=0,
        text="Cascade test chunk text snippet.",
        char_length=32,
        token_count=7,
        start_char=0,
        end_char=32,
    )
    chunk_repo.insert_chunks([chunk])
    
    vec = np.zeros(384, dtype=np.float32)
    emb = Embedding(
        id="emb_cascade",
        chunk_id=chunk.id,
        dimension=384,
        vector=vec.tolist(),
        vector_blob=vec.tobytes(),
    )
    emb_repo.insert_embeddings([emb])
    
    # Delete parent document
    in_memory_db.execute("DELETE FROM documents WHERE id = ?", (doc.id,))
    in_memory_db.commit()
    
    # Chunks and Embeddings must be cascade deleted
    assert chunk_repo.get_chunks_by_document(doc.id) == []
    assert emb_repo.get_embedding_by_chunk_id(chunk.id) is None

