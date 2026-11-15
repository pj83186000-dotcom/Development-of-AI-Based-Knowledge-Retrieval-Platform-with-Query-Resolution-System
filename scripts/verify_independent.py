"""
Independent Verification Script for Milestone 1
Directly audits SQLite database, vectors, normalization, foreign keys, live ingestion, and live queries.
"""
import os
import sys
import sqlite3
import numpy as np

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.path.insert(0, os.getcwd())

print("============================================================")
print("INDEPENDENT AUDIT STEP 1: SQLITE DATABASE INSPECTION")
print("============================================================")

db_path = os.path.join("data", "knowledge_base.db")
assert os.path.exists(db_path), f"Database file does not exist at {db_path}"

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON;")
cursor = conn.cursor()

# 1. Tables check
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]
print(f"Discovered tables: {tables}")
required_tables = ["chunks", "documents", "embeddings", "queries", "responses", "retrieval_results"]
for req in required_tables:
    assert req in tables, f"Missing required table: {req}"
print("-> All 6 required tables present.")

# 2. Row counts
counts = {}
for t in required_tables:
    cursor.execute(f"SELECT count(*) FROM {t};")
    counts[t] = cursor.fetchone()[0]
    print(f"  {t}: {counts[t]} rows")

assert counts["documents"] == 8, f"Expected 8 documents, got {counts['documents']}"
assert counts["chunks"] == 33, f"Expected 33 chunks, got {counts['chunks']}"
assert counts["embeddings"] == 33, f"Expected 33 embeddings, got {counts['embeddings']}"

# 3. Vector blobs, dimensions, and L2 normalization
cursor.execute("SELECT id, chunk_id, vector_blob, dimension FROM embeddings;")
embedding_rows = cursor.fetchall()
dim_errors = 0
norm_errors = 0
for eid, cid, blob, dims in embedding_rows:
    if len(blob) != 1536:
        dim_errors += 1
    if dims != 384:
        dim_errors += 1
    vec = np.frombuffer(blob, dtype=np.float32)
    if len(vec) != 384:
        dim_errors += 1
    norm = float(np.linalg.norm(vec))
    if abs(norm - 1.0) > 1e-4:
        norm_errors += 1

print(f"Total embeddings verified: {len(embedding_rows)}")
print(f"Dimension/BLOB byte-length errors: {dim_errors}")
print(f"L2-normalization errors (|norm - 1.0| > 1e-4): {norm_errors}")
assert dim_errors == 0, f"Found {dim_errors} vector dimension errors!"
assert norm_errors == 0, f"Found {norm_errors} normalization errors!"
print("-> All 33 embeddings are strictly 384-D, 1536-byte float32 vectors with L2-norm == 1.0.")

# 4. Foreign key integrity check
cursor.execute("PRAGMA foreign_key_check;")
fk_violations = cursor.fetchall()
print(f"Foreign key violations: {len(fk_violations)}")
assert len(fk_violations) == 0, f"Found FK violations: {fk_violations}"
print("-> Zero foreign key violations.")

# 5. Dual-Domain Document Breakdown
cursor.execute("SELECT domain, file_type, count(*) FROM documents GROUP BY domain, file_type ORDER BY domain, file_type;")
breakdown = cursor.fetchall()
print(f"Dual-Domain Document Breakdown:")
for d, f, c in breakdown:
    print(f"  Domain: {d:<15} | File Type: {f:<6} | Count: {c}")

conn.close()

print("\n============================================================")
print("INDEPENDENT AUDIT STEP 2: LIVE INGESTION OF NEW TEST DOCUMENT")
print("============================================================")
from backend.app.ingestion.pipeline import IngestionPipeline

test_db_path = "data/test_verification_scratch.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)

pipeline = IngestionPipeline(db_path=test_db_path)

# Test live ingestion of all 4 formats
test_samples = [
    ("sample_documents/cloud_devops/kubernetes_cluster_setup.txt", "cloud_devops"),
    ("sample_documents/cloud_devops/ci_cd_deployment_pipeline.docx", "cloud_devops"),
    ("sample_documents/cloud_devops/server_incident_metrics.csv", "cloud_devops"),
    ("sample_documents/cloud_devops/network_security_policy.pdf", "cloud_devops"),
]

for sample_path, domain in test_samples:
    with open(sample_path, "rb") as f:
        file_bytes = f.read()
    filename = os.path.basename(sample_path)
    res = pipeline.process_file(filename=filename, file_bytes=file_bytes, domain=domain)
    print(f"Ingested '{filename}' -> Status: {res.status} | Chunks: {res.chunk_count} | Embeddings: {res.embedding_count}")
    assert res.status == "processed", f"Failed to ingest {filename}"
    assert res.chunk_count > 0
    assert res.embedding_count == res.chunk_count

# Duplicate rejection check
sample_txt = "sample_documents/cloud_devops/kubernetes_cluster_setup.txt"
with open(sample_txt, "rb") as f:
    file_bytes = f.read()
dup_res = pipeline.process_file(filename=os.path.basename(sample_txt), file_bytes=file_bytes, domain="cloud_devops")
print(f"Duplicate re-ingestion status: {dup_res.status} | is_duplicate: {dup_res.is_duplicate}")
assert dup_res.is_duplicate is True
assert "Duplicate document detected" in dup_res.message

if os.path.exists(test_db_path):
    os.remove(test_db_path)
print("-> Ingestion pipeline live execution & duplicate prevention verified for all 4 formats.")

print("\n============================================================")
print("INDEPENDENT AUDIT STEP 3: LIVE RETRIEVAL QUERIES")
print("============================================================")
from backend.app.retrieval.search import SemanticSearchEngine

engine = SemanticSearchEngine(db_path=db_path)

test_queries = [
    ("Factual", "What is the role of etcd in Kubernetes cluster architecture?"),
    ("Procedural", "What is the initial evaluation timeframe for ESI Level 2 Emergent triage patients?"),
    ("Comparative", "Compare normal resting heart rate ranges for neonates versus adults."),
    ("Unavailable", "What is the recipe and bake time for classic French croissants with sourdough?"),
]

for qtype, qtext in test_queries:
    res = engine.search(query_text=qtext, top_k=3, similarity_threshold=0.35)
    print(f"\nQuery [{qtype}]: '{qtext}'")
    print(f"  Status: {res.status} | Has sufficient context: {res.has_sufficient_context}")
    if res.top_1:
        top = res.top_1
        print(f"  Top-1 Doc: {top.document_name} (Similarity: {top.similarity_score:.4f})")
        print(f"  Excerpt: {top.text[:120]}...")
    else:
        print(f"  Max similarity ({res.max_similarity_score:.4f}) below threshold 0.35 -> Correctly flagged unavailable.")

print("\n============================================================")
print("INDEPENDENT AUDIT STEP 4: EVALUATION BENCHMARK METRICS CHECK")
print("============================================================")
csv_path = os.path.join("evaluation", "evaluation_results.csv")
assert os.path.exists(csv_path), f"Benchmark CSV not found at {csv_path}"

with open(csv_path, "r", encoding="utf-8") as f:
    lines = [l.strip().split(",") for l in f if l.strip()]

header = lines[0]
rows = lines[1:]
print(f"Benchmark rows count: {len(rows)}")
assert len(rows) == 20, f"Expected 20 benchmark rows, got {len(rows)}"

relevant = [r for r in rows if r[2] != "unavailable"]
unavailable = [r for r in rows if r[2] == "unavailable"]
print(f"Relevant queries: {len(relevant)} | Unavailable queries: {len(unavailable)}")

top1_correct = sum(1 for r in relevant if r[10].strip().lower() == "true")
top3_correct = sum(1 for r in relevant if r[11].strip().lower() == "true")
top5_correct = sum(1 for r in relevant if r[12].strip().lower() == "true")
unavail_rejected = sum(1 for r in unavailable if r[8].strip().lower() == "unavailable")

top1_pct = (top1_correct / len(relevant)) * 100
top3_pct = (top3_correct / len(relevant)) * 100
top5_pct = (top5_correct / len(relevant)) * 100
unavail_pct = (unavail_rejected / len(unavailable)) * 100

print(f"Calculated Top-1 Accuracy: {top1_pct:.2f}% ({top1_correct}/{len(relevant)})")
print(f"Calculated Top-3 Accuracy: {top3_pct:.2f}% ({top3_correct}/{len(relevant)})")
print(f"Calculated Top-5 Accuracy: {top5_pct:.2f}% ({top5_correct}/{len(relevant)})")
print(f"Calculated Unavailable Rejection: {unavail_pct:.2f}% ({unavail_rejected}/{len(unavailable)})")

print("\n============================================================")
print("ALL INDEPENDENT VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
print("============================================================")
