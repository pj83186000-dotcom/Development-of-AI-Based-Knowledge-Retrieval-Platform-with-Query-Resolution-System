# Technology Stack & Architectural Justifications

**Project**: AI-Based Knowledge Retrieval Platform with Query Resolution System  
**Milestone**: 1 — Technical Research & Core Foundations  
**Document**: Technology Stack Specification  

---

## 1. Overview of Technology Stack

This document details every library, tool, and framework selected for Milestone 1 of the Knowledge Retrieval Platform. Each choice is evaluated against alternatives and justified based on:
1. **Beginner-friendliness**: Clean, readable APIs that explain foundational concepts rather than hiding them behind layers of complex abstraction.
2. **Technical robustness**: High reliability, active open-source maintenance, and cross-platform stability.
3. **Local independence**: Running embeddings and retrieval locally without requiring paid third-party API keys or constant cloud network connectivity.

```
+─────────────────────────────────────────────────────────────────────────+
|                              PRESENTATION LAYER                         |
|           Vanilla HTML5  •  Modern CSS3  •  Vanilla JavaScript           |
|                Browser Web Speech API (STT & TTS)                       |
+─────────────────────────────────────────────────────────────────────────+
                                    │  HTTP / JSON (REST API)
                                    ▼
+─────────────────────────────────────────────────────────────────────────+
|                              BACKEND API LAYER                          |
|                       FastAPI 0.163  •  Uvicorn 0.54                    |
|                   Pydantic Data Validation & Serialization              |
+─────────────────────────────────────────────────────────────────────────+
                                    │
                                    ▼
+─────────────────────────────────────────────────────────────────────────+
|                          KNOWLEDGE INGESTION ENGINE                     |
|     pypdf (PDF)  •  python-docx (DOCX)  •  pandas (CSV)  •  codecs (TXT)|
|            Text Cleaning  •  Sentence-Aware Sliding Chunker             |
+─────────────────────────────────────────────────────────────────────────+
                                    │
                                    ▼
+─────────────────────────────────────────────────────────────────────────+
|                       EMBEDDINGS & VECTOR OPERATIONS                    |
|          Sentence-Transformers 6.3  •  all-MiniLM-L6-v2 (384-D)         |
|              PyTorch 2.15 (CPU)  •  NumPy 2.5 (Cosine Sim)              |
+─────────────────────────────────────────────────────────────────────────+
                                    │
                                    ▼
+─────────────────────────────────────────────────────────────────────────+
|                              STORAGE LAYER                              |
|                    SQLite 3 (Documents & Chunk Records)                 |
|                   Local File System (Uploaded Originals)                |
+─────────────────────────────────────────────────────────────────────────+
```

---

## 2. Detailed Layer-by-Layer Evaluation

### 2.1 Programming Language & Runtime

#### Chosen: **Python 3.14 (with isolated Virtual Environment `.venv`)**
- **Role**: Core language for backend services, text processing, data science, and vector operations.
- **Why Chosen**: Python is the global standard for AI, machine learning, and natural language processing. Its rich ecosystem allows direct access to state-of-the-art embedding models and text manipulation libraries.
- **Beginner Perspective**: Python has clean, readable syntax that looks like structured pseudocode, making it the most accessible language for a beginner learning RAG architecture.
- **Isolation Strategy**: All project packages are installed inside a local `.venv/` virtual environment, leaving your computer's global Python installation completely unaltered.

---

### 2.2 Backend Web Framework & Server

#### Chosen: **FastAPI (`0.163.0`) + Uvicorn (`0.54.0`)**
- **Role**: Provides the REST API layer connecting our frontend to the ingestion engine and retrieval pipeline.
- **Why Chosen**:
  1. **Automatic Documentation**: FastAPI automatically generates an interactive API documentation interface at `http://localhost:8000/docs` (Swagger UI). Beginners can test endpoints directly in the browser without writing frontend code first.
  2. **Type Safety with Pydantic**: Incoming requests and outgoing responses are strictly validated using standard Python type hints (`str`, `int`, `float`), catching bugs before execution.
  3. **High Performance**: Built on top of Starlette and `asyncio`, offering production-grade throughput.

#### Comparison with Alternatives:
| Framework | Strengths | Weaknesses | Reason for Rejection / Selection |
| :--- | :--- | :--- | :--- |
| **FastAPI** | Auto-docs (`/docs`), Pydantic typing, async support, beginner-friendly | Requires understanding async/await | **SELECTED**: Best balance of developer ergonomics and performance. |
| **Flask** | Very simple micro-framework | No built-in validation, manual swagger docs, synchronous by default | More boilerplate needed to validate schemas. |
| **Django** | Full-stack with built-in admin panel and ORM | Extremely heavy, rigid boilerplate, steep learning curve | Overkill for a lightweight RAG retrieval engine. |

---

### 2.3 Document Text Extraction Suite

Our system supports four document formats: **PDF, DOCX, TXT, and CSV**.

#### 1. PDF Extraction: **`pypdf` (`7.1.0`)**
- **Role**: Reads binary PDF structures and extracts raw textual strings page by page.
- **Why Chosen**: Pure Python library with zero external C/C++ compilation or system-level dependencies (unlike `pdf2image` or `tesseract` which require Poppler and OCR binaries on Windows).
- **Alternative Evaluated**: `PyMuPDF (fitz)` is faster on massive PDFs, but has platform-specific wheel dependencies that can fail on bleeding-edge Python versions. `pypdf` works reliably out of the box.

#### 2. Word Document Extraction: **`python-docx` (`1.2.0`)**
- **Role**: Parses Microsoft Word `.docx` XML archives, extracting text from body paragraphs, headings, and tabular cell grids.
- **Why Chosen**: The de-facto standard in the Python ecosystem for `.docx` manipulation. Clean paragraph and table iteration API.

#### 3. CSV Tabular Processing: **`pandas` (`3.1.1`)**
- **Role**: Parses comma-separated value tables into structured dataframes and reformats rows into descriptive text chunks.
- **Why Chosen**: Standard RAG approaches fail on CSV files if they treat them as plain raw comma-delimited text. With `pandas`, we can transform each row into a structured sentence:
  ```text
  "Record ID 104: Service Name is CloudWatch, Department is DevOps, Monthly Cost is $450, Uptime SLA is 99.9%."
  ```
  This transformation allows dense embedding models to understand semantic relationships across table rows.

#### 4. Plain Text Extraction: **Built-in `open()` with multi-encoding fallback**
- **Role**: Ingests raw `.txt` and `.md` files.
- **Why Chosen**: Native Python standard library. We implement a robust fallback decoding sequence (`utf-8` $\rightarrow$ `latin-1` $\rightarrow$ `cp1252`) to ensure files encoded on different operating systems never trigger unhandled decoding crashes.

---

### 2.4 Vector Embeddings & Numerical Processing

#### 1. Embedding Model: **`sentence-transformers` (`6.3.0`) — `all-MiniLM-L6-v2`**
- **Role**: Transforms text chunks and user queries into 384-dimensional dense vectors.
- **Model Details**:
  - **Architecture**: 6-layer MiniLM transformer with 22.7 million parameters.
  - **Embedding Dimension**: 384 dimensions.
  - **Model File Size**: ~80 MB.
  - **Inference Efficiency**: Designed specifically for high-throughput sentence encoding on standard CPU hardware due to its compact 6-layer architecture (reference: Hugging Face `sentence-transformers/all-MiniLM-L6-v2` model card).
- **Why Chosen**:
  1. **Completely Local & Free**: Runs on your CPU with zero subscription fees, API tokens, or rate limits.
  2. **High Semantic Accuracy**: Ranked as one of the best speed-to-quality ratios on the Massive Text Embedding Benchmark (MTEB).
  3. **Privacy**: Knowledge base documents are never sent across the internet to an external cloud provider.

#### Comparison with Alternatives:
| Embedding Solution | Dimensions | Hosting | Cost | Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **`all-MiniLM-L6-v2`** | **384** | **Local (CPU)** | **Free / Open Source** | **SELECTED**: Fast, reliable, local, privacy-preserving. |
| **OpenAI `text-embedding-3-small`** | 1536 | Cloud API | Pay-per-token ($0.02 / 1M tokens) | High quality, but requires paid API keys and internet access. |
| **BERT-base-uncased** | 768 | Local | Free | 4x larger file size, significantly slower, not pre-tuned for sentence similarity. |

#### 2. Vector Operations & Similarity Search: **`numpy` (`2.5.4`)**
- **Role**: Stores vector matrices in memory and computes mathematical Cosine Similarity.
- **Why Chosen**:
  - Using pure NumPy array math teaches a beginner how vector distance genuinely functions under the hood.
  - For small-to-medium educational collections, vectorized NumPy matrix multiplication executes locally in memory without the overhead of external database network connections or background service daemons.

#### Comparison with Vector Databases:
| Vector Store | Complexity | Infrastructure | Evaluation for Milestone 1 |
| :--- | :--- | :--- | :--- |
| **In-Memory NumPy + SQLite** | **Minimal** | **Zero external servers (Embedded)** | **SELECTED**: Transparent, verifiable, educational, zero black-box dependencies. |
| **ChromaDB / FAISS** | Moderate | Embedded C++ library / local daemon | Excellent for Milestone 2+ when chunk scale exceeds 100,000 items. |
| **Pinecone / Weaviate Cloud** | High | Hosted Cloud Service | Requires network access, accounts, API keys, and vendor lock-in. |

---

### 2.5 Metadata Database & Storage

#### Chosen: **SQLite 3 (`sqlite3` built into Python)**
- **Role**: Stores relational records for uploaded documents, chunk texts, token/character counts, source file metadata, and creation timestamps.
- **Why Chosen**:
  1. **Zero Configuration**: A single `.db` file stored locally in the project directory.
  2. **ACID Compliant**: Guarantees database integrity even if the application process is terminated unexpectedly.
  3. **Built-in Standard Library**: No external database server (like PostgreSQL or MySQL) to install, run, or configure.

---

### 2.6 Testing Suite

#### Chosen: **`pytest` (`9.2.0`)**
- **Role**: Automated unit testing of document extractors, text cleaning, chunking boundaries, embedding shapes, and retrieval ranking.
- **Why Chosen**: 
  - Standard Python `assert` statements instead of verbose `self.assertEqual(...)`.
  - Rich failure reports showing exact variable diffs when a test fails.
  - Seamless test discovery: automatically finds and runs all files matching `test_*.py`.

---

### 2.7 Frontend Interface & Voice

#### Chosen: **Vanilla HTML5, CSS3, Modern JavaScript + Web Speech API**
- **Role**: Lightweight web interface for uploading files, monitoring ingestion status, typing/speaking queries, and viewing retrieved chunks with similarity scores.
- **Why Chosen**:
  1. **Zero Build Step**: No complex Node.js, Webpack, Vite, or React build toolchains to install or debug. A beginner can open and edit `.html` and `.js` files directly.
  2. **Native Web Speech API Support**: Directly accesses browser `SpeechRecognition` and `SpeechSynthesis` without external audio libraries.

---

## 3. Technology Dependency Matrix

| Category | Library / Tool | Version | License | Documentation Link |
| :--- | :--- | :--- | :--- | :--- |
| Runtime | Python | 3.14.3 | PSF License | [https://docs.python.org/3/](https://docs.python.org/3/) |
| API Framework | FastAPI | 0.163.0 | MIT | [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/) |
| ASGI Server | Uvicorn | 0.54.0 | BSD-3-Clause | [https://www.uvicorn.org/](https://www.uvicorn.org/) |
| PDF Extraction | pypdf | 7.1.0 | BSD-3-Clause | [https://pypdf.readthedocs.io/](https://pypdf.readthedocs.io/) |
| DOCX Extraction | python-docx | 1.2.0 | MIT | [https://python-docx.readthedocs.io/](https://python-docx.readthedocs.io/) |
| CSV / Tabular | pandas | 3.1.1 | BSD-3-Clause | [https://pandas.pydata.org/docs/](https://pandas.pydata.org/docs/) |
| Embeddings | sentence-transformers | 6.3.0 | Apache 2.0 | [https://sbert.net/](https://sbert.net/) |
| ML Tensor Backend | PyTorch | 2.15.0+cpu | Modified BSD | [https://pytorch.org/docs/](https://pytorch.org/docs/) |
| Linear Algebra | NumPy | 2.5.4 | BSD-3-Clause | [https://numpy.org/doc/](https://numpy.org/doc/) |
| Database | SQLite | 3.x (Built-in) | Public Domain | [https://www.sqlite.org/docs.html](https://www.sqlite.org/docs.html) |
| Unit Testing | pytest | 9.2.0 | MIT | [https://docs.pytest.org/](https://docs.pytest.org/) |
| Voice Interface | Web Speech API | W3C Standard | W3C Permissive | [https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) |

