"""Semantic retrieval API endpoint for Milestone 1.4 RAG search and evaluation."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.retrieval.evaluator import DualDomainEvaluator, RESULTS_CSV_PATH
from backend.app.retrieval.search import (
    DEFAULT_SIMILARITY_THRESHOLD,
    SemanticSearchEngine,
)

router = APIRouter(prefix="/api/query", tags=["retrieval"])


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Top-K passages to retrieve")
    similarity_threshold: float = Field(
        default=DEFAULT_SIMILARITY_THRESHOLD,
        ge=-1.0,
        le=1.0,
        description="Relevance similarity cutoff score (-1.0 to 1.0)",
    )
    domain: Optional[str] = Field(
        default=None, description="Optional domain filter ('cloud_devops', 'healthcare')"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID for audit logging"
    )


class RetrievedChunkModel(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    domain: str
    chunk_index: int
    text: str
    similarity_score: float
    rank: int


class RetrievalResponse(BaseModel):
    query: str
    query_id: str
    session_id: str
    total_indexed_chunks: int
    max_similarity_score: float
    similarity_threshold: float
    has_sufficient_context: bool
    status: str
    retrieved_chunks: List[RetrievedChunkModel]
    top_1: Optional[RetrievedChunkModel] = None
    top_3: List[RetrievedChunkModel] = []
    top_5: List[RetrievedChunkModel] = []
    message: str


class EvaluationSummaryResponse(BaseModel):
    total_queries: int
    relevant_queries: int
    unavailable_queries: int
    top_1_accuracy: float
    top_3_accuracy: float
    top_5_accuracy: float
    unavailable_rejection_accuracy: float
    similarity_threshold: float
    results_csv: str


def handle_search(request: RetrievalRequest) -> RetrievalResponse:
    """Core synchronous handler for semantic search."""
    cleaned = (request.query or "").strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty or whitespace.",
        )
    
    engine = SemanticSearchEngine()
    try:
        payload = engine.search(
            query_text=cleaned,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            domain=request.domain,
            session_id=request.session_id,
            log_to_db=True,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval error: {str(err)}",
        ) from err

    def _convert_chunk(c) -> RetrievedChunkModel:
        return RetrievedChunkModel(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_name=c.document_name,
            domain=c.domain,
            chunk_index=c.chunk_index,
            text=c.text,
            similarity_score=c.similarity_score,
            rank=c.rank,
        )

    chunks = [_convert_chunk(c) for c in payload.retrieved_chunks]
    top_1 = _convert_chunk(payload.top_1) if payload.top_1 else None
    top_3 = [_convert_chunk(c) for c in payload.top_3]
    top_5 = [_convert_chunk(c) for c in payload.top_5]

    return RetrievalResponse(
        query=payload.query,
        query_id=payload.query_id,
        session_id=payload.session_id,
        total_indexed_chunks=payload.total_indexed_chunks,
        max_similarity_score=payload.max_similarity_score,
        similarity_threshold=payload.similarity_threshold,
        has_sufficient_context=payload.has_sufficient_context,
        status=payload.status,
        retrieved_chunks=chunks,
        top_1=top_1,
        top_3=top_3,
        top_5=top_5,
        message=payload.message,
    )


@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    summary="Semantic vector retrieval and Top-K ranking",
)
def retrieve_query(request: RetrievalRequest) -> RetrievalResponse:
    """Accept natural language query, compute dot-product Cosine Similarity against
    stored chunk embeddings, apply similarity threshold, and return ranked Top-1/3/5 passages."""
    return handle_search(request)


@router.post(
    "/evaluate",
    response_model=EvaluationSummaryResponse,
    summary="Execute dual-domain benchmark suite and compute retrieval accuracy",
)
def evaluate_benchmark(
    similarity_threshold: float = Query(
        default=DEFAULT_SIMILARITY_THRESHOLD, ge=-1.0, le=1.0
    ),
    output_csv_path: Optional[Path] = None,
) -> EvaluationSummaryResponse:
    """Run standardized 20-query evaluation suite across Cloud/DevOps and Healthcare domains.
    Calculates Top-1, Top-3, Top-5 retrieval accuracy and unavailable query rejection rates."""
    csv_target = output_csv_path or RESULTS_CSV_PATH
    evaluator = DualDomainEvaluator(
        similarity_threshold=similarity_threshold,
        output_csv_path=csv_target,
    )
    summary = evaluator.run_benchmark()
    return EvaluationSummaryResponse(
        total_queries=summary["total_queries"],
        relevant_queries=summary["relevant_queries"],
        unavailable_queries=summary["unavailable_queries"],
        top_1_accuracy=summary["top_1_accuracy"],
        top_3_accuracy=summary["top_3_accuracy"],
        top_5_accuracy=summary["top_5_accuracy"],
        unavailable_rejection_accuracy=summary["unavailable_rejection_accuracy"],
        similarity_threshold=summary["similarity_threshold"],
        results_csv=summary["results_csv"],
    )

