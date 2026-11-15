"""Unit tests for embedding generation and 1536-byte BLOB serialization."""

import numpy as np
import pytest

from backend.app.database.models import Chunk
from backend.app.ingestion.embedder import (
    EXPECTED_BLOB_BYTES,
    EXPECTED_DIMENSION,
    generate_embeddings,
    get_embedding_model,
)


def test_embedding_model_singleton():
    m1 = get_embedding_model()
    m2 = get_embedding_model()
    assert m1 is m2


def test_generate_embeddings_empty():
    assert generate_embeddings([]) == []


def test_generate_embeddings_dimensions_and_blob():
    chunks = [
        Chunk(
            id="chk_emb_test_1",
            document_id="doc_test_1",
            chunk_index=0,
            text="Kubernetes cluster orchestration architecture.",
            char_length=46,
            token_count=10,
            start_char=0,
            end_char=46,
        ),
        Chunk(
            id="chk_emb_test_2",
            document_id="doc_test_1",
            chunk_index=1,
            text="Emergency department patient triage protocol.",
            char_length=45,
            token_count=9,
            start_char=46,
            end_char=91,
        ),
    ]
    
    embeddings = generate_embeddings(chunks)
    assert len(embeddings) == 2
    
    for i, emb in enumerate(embeddings):
        assert emb.chunk_id == chunks[i].id
        assert emb.dimension == EXPECTED_DIMENSION
        assert len(emb.vector) == EXPECTED_DIMENSION
        assert emb.vector_blob is not None
        assert len(emb.vector_blob) == EXPECTED_BLOB_BYTES
        
        # Verify deserialization
        arr = np.frombuffer(emb.vector_blob, dtype=np.float32)
        assert len(arr) == EXPECTED_DIMENSION
        assert np.allclose(arr, np.array(emb.vector, dtype=np.float32))

