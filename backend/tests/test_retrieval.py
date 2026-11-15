"""Unit and integration tests for Milestone 1.4 semantic retrieval and evaluation."""

from pathlib import Path
import pytest

from backend.app.database.connection import get_connection, init_db
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.retrieval.evaluator import DualDomainEvaluator
from backend.app.retrieval.search import SemanticSearchEngine

SAMPLE_DIR = Path("sample_documents")


@pytest.fixture(scope="module")
def populated_knowledge_base(tmp_path_factory):
    """Ingest sample documents into a temporary SQLite database once for all retrieval tests."""
    temp_dir = tmp_path_factory.mktemp("retrieval_data")
    db_file = temp_dir / "retrieval_test.sqlite"
    init_db(str(db_file))
    
    pipe = IngestionPipeline(db_path=str(db_file))
    
    # Ingest 4 Cloud/DevOps files
    cloud_files = [
        "kubernetes_cluster_setup.txt",
        "ci_cd_deployment_pipeline.docx",
        "server_incident_metrics.csv",
        "network_security_policy.pdf",
    ]
    for fn in cloud_files:
        with open(SAMPLE_DIR / "cloud_devops" / fn, "rb") as f:
            pipe.process_file(fn, f.read(), domain="cloud_devops")
            
    # Ingest 4 Healthcare files
    health_files = [
        "clinical_trial_protocol.txt",
        "hospital_patient_triage_guidelines.docx",
        "vital_signs_reference_ranges.csv",
        "pediatric_vaccination_schedule.pdf",
    ]
    for fn in health_files:
        with open(SAMPLE_DIR / "healthcare" / fn, "rb") as f:
            pipe.process_file(fn, f.read(), domain="healthcare")
            
    return str(db_file)


def test_empty_corpus_search(tmp_path):
    empty_db = tmp_path / "empty.sqlite"
    init_db(str(empty_db))
    engine = SemanticSearchEngine(db_path=str(empty_db))
    res = engine.search("What is Kubernetes?", top_k=5)
    assert res.status == "empty_corpus"
    assert res.total_indexed_chunks == 0
    assert len(res.retrieved_chunks) == 0


def test_empty_query_rejected(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    with pytest.raises(ValueError, match="cannot be empty"):
        engine.search("")
    with pytest.raises(ValueError, match="cannot be empty"):
        engine.search("    ")


def test_factual_query_retrieval(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    res = engine.search("What is the role of etcd in Kubernetes?", top_k=5, similarity_threshold=0.35)
    
    assert res.has_sufficient_context is True
    assert res.status == "retrieved"
    assert res.max_similarity_score >= 0.35
    assert len(res.retrieved_chunks) >= 1
    assert res.top_1 is not None
    assert res.top_1.document_name == "kubernetes_cluster_setup.txt"
    assert "etcd" in res.top_1.text.lower()


def test_procedural_query_retrieval(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    res = engine.search(
        "What are the triage evaluation timeframes for Level 2 Emergent patients?",
        top_k=5,
        similarity_threshold=0.35,
    )
    
    assert res.has_sufficient_context is True
    assert res.status == "retrieved"
    assert res.top_1 is not None
    assert res.top_1.document_name == "hospital_patient_triage_guidelines.docx"
    assert "level 2" in res.top_1.text.lower() or "emergent" in res.top_1.text.lower()


def test_unavailable_query_below_threshold(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    res = engine.search(
        "What are the professional rules and field dimensions of cricket?",
        top_k=5,
        similarity_threshold=0.35,
    )
    
    assert res.has_sufficient_context is False
    assert res.status == "unavailable"
    assert len(res.retrieved_chunks) == 0
    assert "unavailable in knowledge base" in res.message.lower()


def test_domain_filtering(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    
    # Cloud-only search
    cloud_res = engine.search("vital signs and blood pressure", domain="cloud_devops", similarity_threshold=0.20)
    for c in cloud_res.retrieved_chunks:
        assert c.domain == "cloud_devops"
        
    # Healthcare-only search
    health_res = engine.search("vital signs and blood pressure", domain="healthcare", similarity_threshold=0.20)
    for c in health_res.retrieved_chunks:
        assert c.domain == "healthcare"


def test_top_k_slices(populated_knowledge_base):
    engine = SemanticSearchEngine(db_path=populated_knowledge_base)
    res = engine.search("container deployment architecture", top_k=5, similarity_threshold=0.25)
    
    if len(res.retrieved_chunks) >= 3:
        assert len(res.top_3) == 3
        assert res.top_1 == res.top_3[0]
    if len(res.retrieved_chunks) >= 5:
        assert len(res.top_5) == 5


def test_dual_domain_evaluator(populated_knowledge_base, tmp_path):
    csv_out = tmp_path / "test_evaluation_results.csv"
    evaluator = DualDomainEvaluator(
        db_path=populated_knowledge_base,
        similarity_threshold=0.35,
        output_csv_path=csv_out,
    )
    
    summary = evaluator.run_benchmark()
    
    assert summary["total_queries"] == 20
    assert summary["relevant_queries"] == 15
    assert summary["unavailable_queries"] == 5
    
    # Verify that accuracy is calculated and strictly between 0 and 100
    assert 0.0 <= summary["top_1_accuracy"] <= 100.0
    assert 0.0 <= summary["top_3_accuracy"] <= 100.0
    assert 0.0 <= summary["top_5_accuracy"] <= 100.0
    assert 0.0 <= summary["unavailable_rejection_accuracy"] <= 100.0
    
    # Top-3 accuracy should be >= Top-1 accuracy by definition
    assert summary["top_3_accuracy"] >= summary["top_1_accuracy"]
    assert summary["top_5_accuracy"] >= summary["top_3_accuracy"]
    
    # Verify CSV was written and has 20 data rows
    assert csv_out.exists()
    with open(csv_out, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 21  # 1 header + 20 rows

