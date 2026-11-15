"""Data models and schemas for the Knowledge Retrieval Platform.

Conforms strictly to the architectural specifications in
documentation/data_models.md.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(BaseModel):
    id: str = Field(..., description="Unique document ID (e.g. doc_9f82d1)")
    filename: str = Field(
        ..., min_length=1, max_length=255, description="Original filename with extension"
    )
    file_type: FileType = Field(..., description="Document format type")
    file_size_bytes: int = Field(
        ..., ge=1, description="Size of the uploaded file in bytes"
    )
    file_hash: str = Field(
        ...,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="SHA-256 cryptographic checksum (strictly 64 hex characters)",
    )
    domain: str = Field(
        default="general",
        description="Domain classification (e.g. cloud_devops, healthcare)",
    )
    chunk_count: int = Field(
        default=0, ge=0, description="Total number of chunks produced"
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING, description="Current ingestion lifecycle state"
    )
    upload_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp in UTC",
    )


class Chunk(BaseModel):
    id: str = Field(..., description="Unique chunk ID (e.g. chk_5a6b7c)")
    document_id: str = Field(
        ..., description="Foreign key reference to parent document"
    )
    chunk_index: int = Field(
        ..., ge=0, description="Sequential 0-based position in document"
    )
    text: str = Field(..., min_length=1, description="Cleaned, normalized text snippet")
    char_length: int = Field(..., ge=1, description="Total character count in chunk")
    token_count: int = Field(
        ..., ge=1, description="Estimated token count (approx. words * 1.3)"
    )
    start_char: int = Field(..., ge=0, description="Starting character offset in text")
    end_char: int = Field(..., ge=1, description="Ending character offset in text")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Format metadata (e.g. page_number, row_index)",
    )

    @model_validator(mode="after")
    def validate_offsets(self) -> "Chunk":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be strictly greater than start_char")
        if self.char_length != (self.end_char - self.start_char):
            raise ValueError("char_length must equal (end_char - start_char)")
        if self.char_length != len(self.text):
            raise ValueError("char_length must equal len(text)")
        return self


class Embedding(BaseModel):
    id: str = Field(..., description="Unique embedding ID (e.g. emb_1a2b3c)")
    chunk_id: str = Field(..., description="Foreign key reference to chunk")
    model_name: str = Field(
        default="all-MiniLM-L6-v2", description="Transformer model used"
    )
    dimension: int = Field(
        default=384, description="Vector dimension count (strictly 384 for MiniLM)"
    )
    vector: List[float] = Field(
        ...,
        min_length=384,
        max_length=384,
        description="Exact 384-dimensional dense float vector",
    )
    vector_blob: Optional[bytes] = Field(
        default=None,
        description="Serialized 1536-byte binary float32 BLOB representation",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Generation timestamp in UTC",
    )

    @model_validator(mode="after")
    def validate_vector_dimension(self) -> "Embedding":
        if self.dimension != 384:
            raise ValueError("dimension must be strictly 384")
        if len(self.vector) != 384:
            raise ValueError(
                f"vector must contain exactly 384 elements, got {len(self.vector)}"
            )
        if self.vector_blob is not None and len(self.vector_blob) != 1536:
            raise ValueError(
                f"vector_blob must be exactly 1536 bytes, got {len(self.vector_blob)}"
            )
        return self


class QueryType(str, Enum):
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"
    UNAVAILABLE = "unavailable"
    AMBIGUOUS = "ambiguous"


class Query(BaseModel):
    id: str = Field(..., description="Unique query ID (e.g. qry_3c4d5e)")
    session_id: str = Field(
        ..., description="Session identifier for multi-turn tracking"
    )
    raw_query_text: str = Field(
        ..., min_length=1, max_length=1000, description="Raw query entered by user"
    )
    processed_query_text: Optional[str] = Field(
        None, description="Rewritten search query from Query Understanding Agent"
    )
    query_type: QueryType = Field(
        default=QueryType.FACTUAL, description="Classified query taxonomy"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Submission timestamp in UTC",
    )


class RetrievalResult(BaseModel):
    id: str = Field(..., description="Unique result ID (e.g. res_7e8f9a)")
    query_id: str = Field(..., description="Foreign key reference to query")
    chunk_id: str = Field(..., description="Foreign key reference to chunk")
    document_id: str = Field(..., description="Foreign key reference to document")
    document_name: str = Field(..., description="Cached document filename")
    chunk_text: str = Field(..., description="Cached chunk text content")
    similarity_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Calculated Cosine Similarity score (-1.0 to +1.0)",
    )
    rank: int = Field(
        ..., ge=1, description="Result position index in Top-K ranking (1-based)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Format metadata (e.g. page_number, row_index)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Result generation timestamp in UTC",
    )


class ResponseStatus(str, Enum):
    ANSWERED = "answered"
    CLARIFIED = "clarified"
    UNAVAILABLE = "unavailable"


class ResponseCitation(BaseModel):
    document_name: str
    chunk_index: int
    chunk_id: str


class Response(BaseModel):
    id: str = Field(..., description="Unique response ID (e.g. rsp_9a0b1c)")
    query_id: str = Field(..., description="Reference to parent query")
    response_text: str = Field(
        ..., description="Grounded answer or clarification message"
    )
    citations: List[ResponseCitation] = Field(
        default_factory=list, description="List of source citations backing assertions"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall answer grounding confidence score",
    )
    status: ResponseStatus = Field(
        default=ResponseStatus.ANSWERED, description="Resolution outcome"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Generation timestamp in UTC",
    )

