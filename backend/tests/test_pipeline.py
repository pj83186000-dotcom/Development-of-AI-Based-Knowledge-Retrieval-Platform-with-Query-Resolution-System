"""Integration tests for the end-to-end knowledge base ingestion pipeline."""

from pathlib import Path
import pytest

from backend.app.database.connection import get_connection
from backend.app.database.repository import (
    ChunkRepository,
    DocumentRepository,
    EmbeddingRepository,
)
from backend.app.ingestion.pipeline import IngestionPipeline

SAMPLE_DIR = Path("sample_documents")


@pytest.fixture
def test_pipeline(tmp_path):
    """Create a pipeline instance hooked to a temporary SQLite database."""
    db_file = tmp_path / "pipeline_test.sqlite"
    return IngestionPipeline(db_path=str(db_file))


def test_pipeline_ingest_cloud_devops_samples(test_pipeline):
    cloud_files = [
        ("kubernetes_cluster_setup.txt", "cloud_devops"),
        ("ci_cd_deployment_pipeline.docx", "cloud_devops"),
        ("server_incident_metrics.csv", "cloud_devops"),
        ("network_security_policy.pdf", "cloud_devops"),
    ]
    
    for filename, domain in cloud_files:
        file_path = SAMPLE_DIR / "cloud_devops" / filename
        assert file_path.exists(), f"Missing test file {file_path}"
        with open(file_path, "rb") as f:
            content = f.read()
        
        result = test_pipeline.process_file(
            filename=filename,
            file_bytes=content,
            domain=domain,
            chunk_size=400,
            chunk_overlap=80,
        )
        
        assert result.status == "processed"
        assert result.chunk_count > 0
        assert result.embedding_count == result.chunk_count
        assert result.is_duplicate is False
        assert result.extracted_char_count > 0
        
        # Verify in SQLite
        conn = get_connection(test_pipeline.db_path)
        try:
            doc_repo = DocumentRepository(conn)
            chunk_repo = ChunkRepository(conn)
            emb_repo = EmbeddingRepository(conn)
            
            db_doc = doc_repo.get_document_by_id(result.document_id)
            assert db_doc is not None
            assert db_doc.chunk_count == result.chunk_count
            assert db_doc.file_hash == result.file_hash
            
            chunks = chunk_repo.get_chunks_by_document(result.document_id)
            assert len(chunks) == result.chunk_count
            
            for chk in chunks:
                emb = emb_repo.get_embedding_by_chunk_id(chk.id)
                assert emb is not None
                assert emb.dimension == 384
                assert len(emb.vector) == 384
                assert len(emb.vector_blob) == 1536
        finally:
            conn.close()


def test_pipeline_ingest_healthcare_samples(test_pipeline):
    health_files = [
        ("clinical_trial_protocol.txt", "healthcare"),
        ("hospital_patient_triage_guidelines.docx", "healthcare"),
        ("vital_signs_reference_ranges.csv", "healthcare"),
        ("pediatric_vaccination_schedule.pdf", "healthcare"),
    ]
    
    for filename, domain in health_files:
        file_path = SAMPLE_DIR / "healthcare" / filename
        assert file_path.exists(), f"Missing test file {file_path}"
        with open(file_path, "rb") as f:
            content = f.read()
        
        result = test_pipeline.process_file(
            filename=filename,
            file_bytes=content,
            domain=domain,
            chunk_size=400,
            chunk_overlap=80,
        )
        
        assert result.status == "processed"
        assert result.chunk_count > 0
        assert result.embedding_count == result.chunk_count
        assert result.is_duplicate is False


def test_pipeline_duplicate_file_handling(test_pipeline):
    file_path = SAMPLE_DIR / "cloud_devops" / "server_incident_metrics.csv"
    with open(file_path, "rb") as f:
        content = f.read()
        
    # First ingestion
    res1 = test_pipeline.process_file("server_incident_metrics.csv", content, "cloud_devops")
    assert res1.is_duplicate is False
    
    # Second ingestion of identical content
    res2 = test_pipeline.process_file("server_incident_metrics.csv", content, "cloud_devops")
    assert res2.is_duplicate is True
    assert res2.document_id == res1.document_id
    assert "Duplicate document detected" in res2.message
    
    # Verify database chunk count didn't duplicate
    conn = get_connection(test_pipeline.db_path)
    try:
        chunk_repo = ChunkRepository(conn)
        chunks = chunk_repo.get_chunks_by_document(res1.document_id)
        assert len(chunks) == res1.chunk_count
    finally:
        conn.close()


def test_pipeline_empty_file_rejection(test_pipeline):
    with pytest.raises(ValueError, match="File cannot be empty"):
        test_pipeline.process_file("empty.txt", b"", "general")


def test_pipeline_unsupported_format_rejection(test_pipeline):
    with pytest.raises(ValueError, match="Unsupported file format"):
        test_pipeline.process_file("malicious.exe", b"Binary data", "general")

