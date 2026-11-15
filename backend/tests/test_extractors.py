"""Unit tests for document extractors across PDF, DOCX, TXT, and CSV formats."""

from pathlib import Path
import pytest

from backend.app.database.models import FileType
from backend.app.ingestion.extractors import (
    extract_csv,
    extract_document,
    extract_docx,
    extract_pdf,
    extract_txt,
)

SAMPLE_DIR = Path("sample_documents")


def test_extract_txt_utf8():
    txt_path = SAMPLE_DIR / "cloud_devops" / "kubernetes_cluster_setup.txt"
    assert txt_path.exists(), f"Missing sample file {txt_path}"
    with open(txt_path, "rb") as f:
        file_bytes = f.read()
    
    text, meta = extract_txt(file_bytes)
    assert len(text) > 0
    assert "Kubernetes Cluster Architecture" in text
    assert meta["format"] == "txt"
    assert meta["encoding"] == "utf-8"


def test_extract_txt_cp1252_and_latin1():
    # CP1252 bytes with euro symbol 0x80
    cp1252_bytes = b"Cost estimate: 50 \x80 per server."
    text, meta = extract_txt(cp1252_bytes)
    assert "Cost estimate: 50 € per server." in text
    assert meta["encoding"] == "cp1252"
    
    # Latin-1 bytes with undefined CP1252 byte 0x81 (which raises UnicodeDecodeError in CP1252)
    latin1_bytes = b"Special protocol code \x81 byte"
    text_lat, meta_lat = extract_txt(latin1_bytes)
    assert "Special protocol code" in text_lat
    assert meta_lat["encoding"] == "latin-1"


def test_extract_docx():
    docx_path = SAMPLE_DIR / "cloud_devops" / "ci_cd_deployment_pipeline.docx"
    assert docx_path.exists(), f"Missing sample file {docx_path}"
    with open(docx_path, "rb") as f:
        file_bytes = f.read()
        
    text, meta = extract_docx(file_bytes)
    assert len(text) > 0
    assert "Continuous Integration and Deployment Pipeline" in text
    assert "Automated Verification Stages" in text
    assert meta["format"] == "docx"
    assert meta["paragraph_count"] > 0
    assert meta["table_count"] > 0


def test_extract_csv():
    csv_path = SAMPLE_DIR / "cloud_devops" / "server_incident_metrics.csv"
    assert csv_path.exists(), f"Missing sample file {csv_path}"
    with open(csv_path, "rb") as f:
        file_bytes = f.read()
        
    text, meta = extract_csv(file_bytes)
    assert len(text) > 0
    assert "INC-101" in text
    assert "kube-proxy" in text
    assert meta["format"] == "csv"
    assert meta["row_count"] >= 5
    assert "incident_id" in meta["columns"]


def test_extract_pdf():
    pdf_path = SAMPLE_DIR / "cloud_devops" / "network_security_policy.pdf"
    assert pdf_path.exists(), f"Missing sample file {pdf_path}"
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
        
    text, meta = extract_pdf(file_bytes)
    assert len(text) > 0
    assert "Cloud Network Security and Zero-Trust Policy" in text
    assert meta["format"] == "pdf"
    assert meta["page_count"] >= 1


def test_extract_invalid_pdf():
    with pytest.raises(ValueError, match="Failed to extract text from PDF"):
        extract_pdf(b"Not a valid PDF byte string")


def test_extract_invalid_docx():
    with pytest.raises(ValueError, match="Failed to extract text from DOCX"):
        extract_docx(b"Not a valid DOCX byte string")


def test_extract_empty_csv():
    with pytest.raises(ValueError):
        extract_csv(b"")


def test_extract_document_router():
    txt_path = SAMPLE_DIR / "healthcare" / "clinical_trial_protocol.txt"
    with open(txt_path, "rb") as f:
        file_bytes = f.read()
    
    text, meta = extract_document(file_bytes, FileType.TXT)
    assert "Clinical Trial Protocol" in text

