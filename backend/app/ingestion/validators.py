"""Validation utilities for file uploads, size checks, and cryptographic hashes."""

import hashlib
import uuid
from pathlib import Path
from typing import Tuple

from backend.app.database.models import FileType

# Configurable limits
DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_MIN_FILE_SIZE_BYTES = 1  # 1 byte

SUPPORTED_EXTENSIONS = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".txt": FileType.TXT,
    ".csv": FileType.CSV,
}


def validate_file_format(filename: str) -> FileType:
    """Validate that the file has a supported extension and return its FileType enum.
    
    Raises ValueError if unsupported.
    """
    ext = Path(filename).suffix.lower()
    if not ext or ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS.keys())
        raise ValueError(
            f"Unsupported file format '{ext or 'unknown'}'. Supported formats are: {supported}"
        )
    return SUPPORTED_EXTENSIONS[ext]


def validate_file_size(
    file_bytes: bytes,
    min_size: int = DEFAULT_MIN_FILE_SIZE_BYTES,
    max_size: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> int:
    """Validate that the file size is within acceptable boundaries.
    
    Raises ValueError if 0 bytes or exceeds max_size.
    """
    size = len(file_bytes)
    if size < min_size:
        raise ValueError(f"File cannot be empty (received {size} bytes, minimum is {min_size} byte).")
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise ValueError(
            f"File size exceeds maximum allowed limit of {max_mb:.1f} MB (received {actual_mb:.2f} MB)."
        )
    return size


def compute_sha256(file_bytes: bytes) -> str:
    """Compute the 64-character lowercase hexadecimal SHA-256 hash of file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def generate_document_id() -> str:
    """Generate a unique document ID prefixed with 'doc_'."""
    return f"doc_{uuid.uuid4().hex[:12]}"


def generate_chunk_id() -> str:
    """Generate a unique chunk ID prefixed with 'chk_'."""
    return f"chk_{uuid.uuid4().hex[:12]}"


def generate_embedding_id() -> str:
    """Generate a unique embedding ID prefixed with 'emb_'."""
    return f"emb_{uuid.uuid4().hex[:12]}"

