"""Vector embedding generation module using Sentence-Transformers.

Generates 384-dimensional dense vectors using all-MiniLM-L6-v2,
verifies dimensions and serializes to 1536-byte float32 BLOBs.
"""

import os
from typing import List, Optional
import numpy as np

# Force offline mode for local files when available
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from sentence_transformers import SentenceTransformer

from backend.app.database.models import Chunk, Embedding
from backend.app.ingestion.validators import generate_embedding_id

MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_DIMENSION = 384
EXPECTED_BLOB_BYTES = 1536

_CACHED_MODEL: Optional[SentenceTransformer] = None


def get_embedding_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    """Return cached SentenceTransformer model instance (lazy singleton)."""
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        try:
            # Try offline cached loading first
            _CACHED_MODEL = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            # Fallback if local_files_only raises
            _CACHED_MODEL = SentenceTransformer(model_name)
    return _CACHED_MODEL


def generate_embeddings(
    chunks: List[Chunk],
    model_name: str = MODEL_NAME,
) -> List[Embedding]:
    """Generate dense vector embeddings for a list of Chunks.
    
    Verifies that:
    1. Output array shape is (N, 384).
    2. Vector coordinates are float32.
    3. Serialized binary BLOB is strictly 1536 bytes (384 * 4).
    
    Args:
        chunks: List of Chunk models to embed.
        model_name: Transformer model name (default: all-MiniLM-L6-v2).
        
    Returns:
        List of validated Embedding models.
    """
    if not chunks:
        return []
    
    model = get_embedding_model(model_name)
    texts = [c.text for c in chunks]
    
    # Generate normalized float32 embeddings
    vectors: np.ndarray = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    
    # Ensure float32 dtype
    if vectors.dtype != np.float32:
        vectors = vectors.astype(np.float32)
    
    # Validate dimensions
    if len(vectors.shape) == 1:
        vectors = np.expand_dims(vectors, axis=0)
    
    num_vectors, dim = vectors.shape
    if dim != EXPECTED_DIMENSION:
        raise ValueError(
            f"Embedding model produced {dim} dimensions, expected strictly {EXPECTED_DIMENSION}."
        )
    if num_vectors != len(chunks):
        raise ValueError(
            f"Expected {len(chunks)} embeddings, but received {num_vectors}."
        )
    
    embeddings: List[Embedding] = []
    for i, chunk in enumerate(chunks):
        vec = vectors[i]
        blob = vec.tobytes()
        
        # Verify 1536-byte BLOB size
        if len(blob) != EXPECTED_BLOB_BYTES:
            raise ValueError(
                f"Serialized vector BLOB length is {len(blob)} bytes, expected strictly {EXPECTED_BLOB_BYTES}."
            )
        
        emb_obj = Embedding(
            id=generate_embedding_id(),
            chunk_id=chunk.id,
            model_name=model_name,
            dimension=EXPECTED_DIMENSION,
            vector=vec.tolist(),
            vector_blob=blob,
        )
        embeddings.append(emb_obj)
    
    return embeddings

