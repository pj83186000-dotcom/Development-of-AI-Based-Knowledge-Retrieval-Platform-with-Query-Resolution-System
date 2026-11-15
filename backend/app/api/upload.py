"""Upload and document management REST API endpoints for FastAPI.

Provides file upload, format/size validation, pipeline execution, and status retrieval
using Python standard library multipart parsing to avoid additional package dependencies.
"""

import email
from email.policy import default
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from backend.app.database.connection import get_connection
from backend.app.database.models import Document, DocumentStatus, FileType
from backend.app.database.repository import DocumentRepository
from backend.app.ingestion.chunker import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from backend.app.ingestion.pipeline import IngestionPipeline, IngestionResult

router = APIRouter(prefix="/api/documents", tags=["documents"])


class UploadResponse(BaseModel):
    success: bool
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    domain: str
    extracted_character_count: int
    chunk_count: int
    embedding_status: str
    is_duplicate: bool
    message: str


class DocumentStatusResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    domain: str
    chunk_count: int
    status: str
    upload_timestamp: str


def handle_upload(
    filename: str,
    file_bytes: bytes,
    domain: str = "general",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> UploadResponse:
    """Core synchronous handler that runs the ingestion pipeline and returns an UploadResponse.
    
    Raises HTTPException(400) on validation error, or HTTPException(500) on unexpected error.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be provided.",
        )
    
    pipeline = IngestionPipeline()
    try:
        result: IngestionResult = pipeline.process_file(
            filename=filename,
            file_bytes=file_bytes,
            domain=domain,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion processing error: {str(err)}",
        ) from err

    return UploadResponse(
        success=True,
        document_id=result.document_id,
        filename=result.filename,
        file_type=result.file_type,
        file_size_bytes=result.file_size_bytes,
        file_hash=result.file_hash,
        domain=result.domain,
        extracted_character_count=result.extracted_char_count,
        chunk_count=result.chunk_count,
        embedding_status="Generated (384-D dense float32, 1536-byte BLOB)",
        is_duplicate=result.is_duplicate,
        message=result.message,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document into the knowledge base",
)
async def upload_document(
    request: Request,
    filename: Optional[str] = Query(None, description="Filename with extension if uploading raw body"),
    domain: Optional[str] = Query("general", description="Domain classification (e.g. cloud_devops, healthcare)"),
    chunk_size: int = Query(DEFAULT_CHUNK_SIZE, description="Target chunk size in characters (300-500)"),
    chunk_overlap: int = Query(DEFAULT_CHUNK_OVERLAP, description="Chunk overlap in characters (50-100)"),
) -> UploadResponse:
    """Accept and process an uploaded document through the M1.3 ingestion pipeline.
    
    Supports both multipart/form-data (standard browser and HTTP client file uploads)
    and raw body uploads with query/header parameters without requiring external C-extensions.
    """
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    
    target_filename = filename
    target_bytes = b""
    target_domain = domain or "general"
    target_chunk_size = chunk_size
    target_chunk_overlap = chunk_overlap

    if "multipart/form-data" in content_type:
        header = f"Content-Type: {content_type}\r\n\r\n".encode("latin-1")
        msg = email.message_from_bytes(header + body, policy=default)
        
        extracted_file = False
        for part in msg.iter_parts():
            part_filename = part.get_filename()
            part_name = part.get_param("name", header="content-disposition")
            
            if part_filename:
                target_filename = part_filename
                payload = part.get_payload(decode=True)
                target_bytes = payload if payload is not None else b""
                extracted_file = True
            elif part_name:
                text_val = part.get_content().strip()
                if part_name == "domain" and text_val:
                    target_domain = text_val
                elif part_name == "chunk_size" and text_val.isdigit():
                    target_chunk_size = int(text_val)
                elif part_name == "chunk_overlap" and text_val.isdigit():
                    target_chunk_overlap = int(text_val)
        
        if not extracted_file and not target_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file attached in multipart form submission.",
            )
    else:
        # Raw bytes upload
        if not target_filename:
            target_filename = request.headers.get("x-filename")
        if not target_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename must be provided via query parameter '?filename=...' or 'X-Filename' header.",
            )
        target_bytes = body

    return handle_upload(
        filename=target_filename,
        file_bytes=target_bytes,
        domain=target_domain,
        chunk_size=target_chunk_size,
        chunk_overlap=target_chunk_overlap,
    )


@router.get(
    "/status/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Get ingestion status and metadata for a document",
)
def get_document_status(document_id: str) -> DocumentStatusResponse:
    """Retrieve document metadata and ingestion status from SQLite."""
    conn = get_connection()
    try:
        repo = DocumentRepository(conn)
        doc = repo.get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )
        return DocumentStatusResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type.value,
            file_size_bytes=doc.file_size_bytes,
            file_hash=doc.file_hash,
            domain=doc.domain,
            chunk_count=doc.chunk_count,
            status=doc.status.value,
            upload_timestamp=doc.upload_timestamp.isoformat(),
        )
    finally:
        conn.close()


@router.get(
    "/list",
    response_model=List[DocumentStatusResponse],
    summary="List all documents registered in the knowledge base",
)
def list_documents(domain: Optional[str] = None) -> List[DocumentStatusResponse]:
    """Retrieve all ingested documents, optionally filtered by domain."""
    conn = get_connection()
    try:
        repo = DocumentRepository(conn)
        docs = repo.list_documents(domain=domain)
        return [
            DocumentStatusResponse(
                id=d.id,
                filename=d.filename,
                file_type=d.file_type.value,
                file_size_bytes=d.file_size_bytes,
                file_hash=d.file_hash,
                domain=d.domain,
                chunk_count=d.chunk_count,
                status=d.status.value,
                upload_timestamp=d.upload_timestamp.isoformat(),
            )
            for d in docs
        ]
    finally:
        conn.close()
