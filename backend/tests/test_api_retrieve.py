"""Unit tests for FastAPI retrieval and evaluation API endpoints."""

from pathlib import Path
import pytest
from fastapi import HTTPException

from backend.app.api.retrieve import (
    RetrievalRequest,
    evaluate_benchmark,
    handle_search,
)
from backend.app.database.connection import init_db
from backend.app.ingestion.pipeline import IngestionPipeline

SAMPLE_DIR = Path("sample_documents")


@pytest.fixture(scope="module")
def populated_api_db(tmp_path_factory, monkeypatch_module=None):
    temp_dir = tmp_path_factory.mktemp("api_retrieval_data")
    db_file = temp_dir / "api_retrieval.sqlite"
    init_db(str(db_file))
    
    pipe = IngestionPipeline(db_path=str(db_file))
    with open(SAMPLE_DIR / "cloud_devops" / "kubernetes_cluster_setup.txt", "rb") as f:
        pipe.process_file("kubernetes_cluster_setup.txt", f.read(), domain="cloud_devops")
    with open(SAMPLE_DIR / "healthcare" / "vital_signs_reference_ranges.csv", "rb") as f:
        pipe.process_file("vital_signs_reference_ranges.csv", f.read(), domain="healthcare")
        
    return str(db_file)


def test_api_handle_search_valid(populated_api_db, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_DB_PATH", populated_api_db)
    
    req = RetrievalRequest(query="What is etcd in Kubernetes?", top_k=3, similarity_threshold=0.35)
    res = handle_search(req)
    
    assert res.has_sufficient_context is True
    assert res.status == "retrieved"
    assert len(res.retrieved_chunks) >= 1
    assert res.top_1 is not None
    assert res.top_1.document_name == "kubernetes_cluster_setup.txt"


def test_api_handle_search_unavailable(populated_api_db, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_DB_PATH", populated_api_db)
    
    req = RetrievalRequest(query="How to play tennis in Wimbledon?", top_k=3, similarity_threshold=0.35)
    res = handle_search(req)
    
    assert res.has_sufficient_context is False
    assert res.status == "unavailable"
    assert len(res.retrieved_chunks) == 0


def test_api_handle_search_empty_query():
    req = RetrievalRequest(query="   ", top_k=3)
    with pytest.raises(HTTPException) as exc_info:
        handle_search(req)
    assert exc_info.value.status_code == 400


def test_api_evaluate_benchmark_endpoint(populated_api_db, monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_BASE_DB_PATH", populated_api_db)
    test_csv = tmp_path / "test_api_eval.csv"
    
    summary = evaluate_benchmark(similarity_threshold=0.35, output_csv_path=test_csv)
    assert summary.total_queries == 20
    assert summary.relevant_queries > 0
    assert 0.0 <= summary.top_1_accuracy <= 100.0
    assert test_csv.exists()

