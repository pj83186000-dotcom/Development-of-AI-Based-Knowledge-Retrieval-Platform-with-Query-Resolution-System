"""API integration tests for FastAPI document upload and management endpoints."""

from pathlib import Path
import pytest
from fastapi import HTTPException

from backend.app.api.upload import (
    get_document_status,
    handle_upload,
    list_documents,
)
from backend.app.database.connection import init_db
from backend.app.main import root

SAMPLE_DIR = Path("sample_documents")


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Point application to a temporary isolated SQLite database for API tests."""
    db_file = tmp_path / "api_test.sqlite"
    monkeypatch.setenv("KNOWLEDGE_BASE_DB_PATH", str(db_file))
    init_db(str(db_file))
    yield


def test_api_root_endpoint():
    data = root()
    assert data["status"] == "online"
    assert "pdf" in data["supported_formats"]
    assert "upload" in data["endpoints"]


def test_api_upload_valid_document():
    file_path = SAMPLE_DIR / "cloud_devops" / "kubernetes_cluster_setup.txt"
    with open(file_path, "rb") as f:
        content = f.read()
    
    response = handle_upload(
        filename="kubernetes_cluster_setup.txt",
        file_bytes=content,
        domain="cloud_devops",
        chunk_size=400,
        chunk_overlap=80,
    )
    
    assert response.success is True
    assert response.document_id.startswith("doc_")
    assert response.chunk_count > 0
    assert response.is_duplicate is False
    assert "384-D" in response.embedding_status


def test_api_upload_duplicate_detection():
    file_path = SAMPLE_DIR / "healthcare" / "vital_signs_reference_ranges.csv"
    with open(file_path, "rb") as f:
        content = f.read()
    
    res1 = handle_upload(
        filename="vital_signs_reference_ranges.csv",
        file_bytes=content,
        domain="healthcare",
    )
    assert res1.is_duplicate is False
    doc_id = res1.document_id
    
    # Second upload of identical content
    res2 = handle_upload(
        filename="vital_signs_reference_ranges.csv",
        file_bytes=content,
        domain="healthcare",
    )
    assert res2.is_duplicate is True
    assert res2.document_id == doc_id
    assert "Duplicate document detected" in res2.message


def test_api_upload_empty_file_rejected():
    with pytest.raises(HTTPException) as exc_info:
        handle_upload(filename="empty.txt", file_bytes=b"", domain="general")
    assert exc_info.value.status_code == 400
    assert "cannot be empty" in exc_info.value.detail


def test_api_upload_unsupported_format_rejected():
    with pytest.raises(HTTPException) as exc_info:
        handle_upload(filename="program.exe", file_bytes=b"MZ\x90...", domain="general")
    assert exc_info.value.status_code == 400
    assert "Unsupported file format" in exc_info.value.detail


def test_api_get_document_status_and_list():
    file_path = SAMPLE_DIR / "healthcare" / "clinical_trial_protocol.txt"
    with open(file_path, "rb") as f:
        content = f.read()
    
    res_upload = handle_upload(
        filename="clinical_trial_protocol.txt",
        file_bytes=content,
        domain="healthcare",
    )
    doc_id = res_upload.document_id
    
    # Fetch status
    status_data = get_document_status(doc_id)
    assert status_data.id == doc_id
    assert status_data.status == "processed"
    assert status_data.domain == "healthcare"
    
    # 404 for non-existent document
    with pytest.raises(HTTPException) as exc_info:
        get_document_status("doc_non_existent")
    assert exc_info.value.status_code == 404
    
    # List documents
    docs = list_documents(domain="healthcare")
    assert len(docs) >= 1
    assert any(d.id == doc_id for d in docs)
