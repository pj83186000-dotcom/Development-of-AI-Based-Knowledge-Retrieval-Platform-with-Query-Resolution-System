"""Script to ingest all sample documents into the primary knowledge base and execute the full Dual-Domain Benchmark evaluation."""

import os
import sys

sys.path.insert(0, os.getcwd())
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
from pathlib import Path

from backend.app.database.connection import init_db
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.retrieval.evaluator import DualDomainEvaluator

SAMPLE_DIR = Path("sample_documents")
DB_PATH = "data/knowledge_base.db"


def main():
    print("=" * 60)
    print("INITIALIZING PRIMARY KNOWLEDGE BASE & INGESTING SAMPLES")
    print("=" * 60)
    
    init_db(DB_PATH)
    pipeline = IngestionPipeline(db_path=DB_PATH)
    
    # 1. Ingest Cloud/DevOps Documents
    cloud_files = [
        "kubernetes_cluster_setup.txt",
        "ci_cd_deployment_pipeline.docx",
        "server_incident_metrics.csv",
        "network_security_policy.pdf",
    ]
    for fn in cloud_files:
        p = SAMPLE_DIR / "cloud_devops" / fn
        with open(p, "rb") as f:
            res = pipeline.process_file(fn, f.read(), domain="cloud_devops")
            print(f"  [Cloud/DevOps] {fn:<35} -> Chunks: {res.chunk_count}, Embeddings: {res.embedding_count}, Status: {res.status}")
            
    # 2. Ingest Healthcare Documents
    health_files = [
        "clinical_trial_protocol.txt",
        "hospital_patient_triage_guidelines.docx",
        "vital_signs_reference_ranges.csv",
        "pediatric_vaccination_schedule.pdf",
    ]
    for fn in health_files:
        p = SAMPLE_DIR / "healthcare" / fn
        with open(p, "rb") as f:
            res = pipeline.process_file(fn, f.read(), domain="healthcare")
            print(f"  [Healthcare]   {fn:<35} -> Chunks: {res.chunk_count}, Embeddings: {res.embedding_count}, Status: {res.status}")

    print("\n" + "=" * 60)
    print("RUNNING DUAL-DOMAIN BENCHMARK EVALUATION (20 QUERIES)")
    print("=" * 60)
    
    evaluator = DualDomainEvaluator(
        db_path=DB_PATH,
        similarity_threshold=0.35,
        output_csv_path=Path("evaluation/evaluation_results.csv"),
    )
    summary = evaluator.run_benchmark()
    
    print("\nBENCHMARK EVALUATION RESULTS SUMMARY:")
    print(f"  Total Queries Tested:           {summary['total_queries']}")
    print(f"  Relevant Queries:               {summary['relevant_queries']}")
    print(f"  Unavailable / Out-of-Domain:    {summary['unavailable_queries']}")
    print(f"  Similarity Threshold:           {summary['similarity_threshold']}")
    print(f"  Top-1 Retrieval Accuracy:       {summary['top_1_accuracy']}%")
    print(f"  Top-3 Retrieval Accuracy:       {summary['top_3_accuracy']}%")
    print(f"  Top-5 Retrieval Accuracy:       {summary['top_5_accuracy']}%")
    print(f"  Unavailable Rejection Accuracy: {summary['unavailable_rejection_accuracy']}%")
    print(f"  Results CSV Saved To:           {summary['results_csv']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
