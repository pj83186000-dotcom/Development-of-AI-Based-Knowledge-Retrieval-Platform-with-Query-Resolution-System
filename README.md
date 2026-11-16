# AI-Based Knowledge Retrieval Platform with Query Resolution System

An enterprise-grade, retrieval-augmented generation (RAG) platform with multi-agent orchestration, semantic vector retrieval, and multi-format document ingestion.

[![Milestone 1](https://img.shields.io/badge/Milestone%201-Completed%20%26%20Verified-brightgreen)](#milestone-1-status)
[![Tests](https://img.shields.io/badge/Tests-51%20passing-success)](#automated-tests)
[![Python](https://img.shields.io/badge/Python-3.14%20%7C%203.11-blue)](#prerequisites)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](#license)

---

## Project Overview

This platform ingests corporate and technical documents across heterogeneous formats, constructs semantic vector representations, and provides grounded retrieval with exact source citations.

### Milestone 1 Status: Completed & Fully Tested

- **M1.1: Research & Technical Understanding**: Complete technical foundation and stack choices ([documentation/research_document.md](documentation/research_document.md), [documentation/technology_stack.md](documentation/technology_stack.md)).
- **M1.2: System Architecture & Data Models**: Architecture diagrams, 5-agent specifications, and schemas ([documentation/system_architecture.md](documentation/system_architecture.md), [documentation/data_models.md](documentation/data_models.md)).
- **M1.3: Knowledge Base Ingestion Pipeline**: Ingestion engine for PDF, DOCX, TXT, and CSV documents with NFKC normalization, sliding-window chunking, 384-D dense embeddings (`all-MiniLM-L6-v2`), and SQLite persistence.
- **M1.4: Semantic Retrieval Pipeline & Benchmark**: Exact dot product Cosine Similarity search ($S = Q \cdot D^T$), Top-1/3/5 ranking, 0.35 threshold filtering, and dual-domain evaluation across Cloud/DevOps and Healthcare.

---

## Architecture & Data Flow

```text
User Query / Document Upload
            │
            ▼
┌───────────────────────────┐
│     FastAPI Endpoints     │
│  /api/documents/upload    │
│  /api/query/retrieve      │
└─────────────┬─────────────┘
              │
      ┌───────┴───────┐
      ▼               ▼
┌──────────────┐┌──────────────┐
│  Ingestion   ││  Retrieval   │
│   Pipeline   ││    Engine    │
│  • Extractor ││  • Query Emb │
│  • Cleaner   ││  • Cosine Sim│
│  • Chunker   ││  • Threshold │
│  • Embedder  ││  • Top-K     │
└──────┬───────┘└──────┬───────┘
       │               │
       ▼               ▼
┌──────────────────────────────┐
│  SQLite + In-Memory Vectors  │
│  data/knowledge_base.db      │
│  • documents (8)             │
│  • chunks (33)               │
│  • embeddings (33, 384-D)    │
└──────────────────────────────┘
```

---

## Dual-Domain Benchmark Results

The evaluation benchmark was executed across 20 queries spanning Cloud/DevOps and Healthcare domains (Factual, Procedural, Comparative, and Unavailable categories):

| Metric | Target | Measured Result |
| :--- | :--- | :--- |
| **Total Queries Evaluated** | 20 | **20** |
| **Top-1 Retrieval Accuracy** | Benchmark | **93.33%** (14 / 15 relevant queries) |
| **Top-3 Retrieval Accuracy** | Benchmark | **100.0%** (15 / 15 relevant queries) |
| **Top-5 Retrieval Accuracy** | Benchmark | **100.0%** (15 / 15 relevant queries) |
| **Unavailable Query Rejection Rate** | Benchmark | **80.0%** (4 / 5 queries rejected below 0.35) |
| **Unit & Integration Tests** | 100% pass | **51 / 51 passed** |

Raw query-level evaluation data is recorded in [evaluation/evaluation_results.csv](evaluation/evaluation_results.csv).

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers (upload, retrieve, evaluate)
│   │   ├── database/        # SQLite DDL schema, models, repository, connection
│   │   ├── ingestion/       # Extractors (PDF, DOCX, TXT, CSV), cleaner, chunker, embedder
│   │   ├── retrieval/       # Vector search engine, dual-domain benchmark evaluator
│   │   └── main.py          # Root FastAPI application
│   └── tests/               # 51 unit & integration tests
├── data/                    # SQLite database (knowledge_base.db)
├── documentation/           # Milestone specifications and progress trackers
│   ├── research_document.md
│   ├── technology_stack.md
│   ├── system_architecture.md
│   ├── data_models.md
│   └── milestone1_progress.md
├── evaluation/              # Benchmark evaluation results CSV
├── sample_documents/        # 8 dual-domain educational documents (Cloud & Healthcare)
├── scripts/                 # Ingestion, benchmark, and verification scripts
├── requirements.txt         # Project dependencies
└── pytest.ini               # Pytest configuration
```

---

## Quick Start & Installation

### 1. Prerequisites
- Python 3.11 or Python 3.14
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/pj83186000-dotcom/Development-of-AI-Based-Knowledge-Retrieval-Platform-with-Query-Resolution-System.git
cd Development-of-AI-Based-Knowledge-Retrieval-Platform-with-Query-Resolution-System
```

### 3. Create & Activate Virtual Environment
```bash
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Automated Test Suite
```bash
pytest
```
*Expected: 51 passed.*

### 6. Run Ingestion & Benchmark Suite
```bash
python scripts/run_dual_domain_evaluation.py
```

### 7. Start the FastAPI Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/`

---

## API Endpoints

### 1. Document Upload
- **`POST /api/documents/upload`**  
  Uploads and indexes PDF, DOCX, TXT, or CSV files. Enforces SHA-256 duplicate prevention.

### 2. Semantic Query Retrieval
- **`POST /api/query/retrieve`**  
  Computes Cosine Similarity dot product against chunk vectors, applies relevance threshold ($0.35$), and returns ranked Top-1/3/5 passages with document citations.

### 3. Benchmark Evaluation
- **`POST /api/query/evaluate`**  
  Runs the standardized 20-query evaluation suite across Cloud/DevOps and Healthcare domains and returns live retrieval accuracy metrics.

---

## Roadmap

- [x] **Milestone 1:** Research, System Architecture, Knowledge Ingestion, Semantic Retrieval & Dual-Domain Benchmark
- [ ] **Milestone 2:** Multi-Agent Orchestration (5 Agents), LLM Response Generation, Citations & Voice Interaction (Web Speech API)
- [ ] **Milestone 3:** Interactive Web Interface, Real-Time Audio Waveforms, Evaluation Dashboard & Deployment

---

## License

This project is licensed under the MIT License.

