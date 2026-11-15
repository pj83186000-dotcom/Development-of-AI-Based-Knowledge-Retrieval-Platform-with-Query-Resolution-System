# M1.1 Research and Technical Understanding

**Project**: AI-Based Knowledge Retrieval Platform with Query Resolution System  
**Milestone**: 1 — Technical Research & Core Foundations  
**Target Audience**: Beginner to Intermediate Software & AI Developers  

---

## Table of Contents
1. [Introduction to Retrieval-Augmented Generation (RAG)](#1-introduction-to-retrieval-augmented-generation-rag)
   - 1.1 What is RAG and Why Does It Matter?
   - 1.2 End-to-End RAG Workflow
   - 1.3 Key Benefits and Inherent Limitations
2. [Multi-Agent Query Resolution & Orchestration](#2-multi-agent-query-resolution--orchestration)
   - 2.1 The Need for Multi-Agent Systems
   - 2.2 Roles of the 5 Specialized Agents
   - 2.3 Orchestration Topologies and Information Flow
3. [Semantic Similarity and Vector Embeddings](#3-semantic-similarity-and-vector-embeddings)
   - 3.1 Understanding Vector Embeddings
   - 3.2 High-Dimensional Embedding Spaces
   - 3.3 Similarity Metrics: Cosine Similarity, Dot Product, and Euclidean Distance
4. [Document Chunking and Vector Search](#4-document-chunking-and-vector-search)
   - 4.1 The Importance of Document Chunking
   - 4.2 Chunking Strategies & Overlap Rationale
   - 4.3 Vector Indexing and Search Algorithms
5. [Web Speech API: Speech-to-Text & Text-to-Speech](#5-web-speech-api-speech-to-text--text-to-speech)
   - 5.1 Overview and Browser Architecture
   - 5.2 SpeechRecognition (Speech-to-Text / STT)
   - 5.3 SpeechSynthesis (Text-to-Speech / TTS)
   - 5.4 Advantages, Limitations, and Fallbacks
6. [Architectural Decisions & Technical Reasoning](#6-architectural-decisions--technical-reasoning)
7. [Technical References and Documentation Links](#7-technical-references-and-documentation-links)

---

## 1. Introduction to Retrieval-Augmented Generation (RAG)

### 1.1 What is RAG and Why Does It Matter?
Large Language Models (LLMs) such as GPT-4, Gemini, and Claude possess extensive general knowledge gained during pre-training. However, in production applications, they face two fundamental limitations:
1. **Knowledge Cutoffs & Private Data**: An LLM cannot know private internal documents, internal company policies, or events that occurred after its training cutoff date.
2. **Hallucination**: When an LLM lacks specific factual knowledge, it often generates plausible-sounding but completely fabricated assertions.

**Retrieval-Augmented Generation (RAG)**—first formalized by Lewis et al. (2020) at Meta AI—addresses this limitation. Instead of relying solely on parametric memory (the model's static internal weights), RAG integrates a non-parametric knowledge base:
- **Retrieval**: Locates relevant snippets of text from an external document repository based on semantic similarity to the user's query.
- **Augmentation**: Inserts those retrieved snippets into the prompt as verified factual context.
- **Generation**: Instructs the LLM to synthesize an answer grounded strictly in that supplied context, citing the exact sources.

```
+---------------+     +-----------------------+     +-------------------------------+
|  User Query   | --> |  Retrieval Mechanism  | --> | Relevant Document Passages    |
+---------------+     +-----------------------+     +-------------------------------+
                                                                    │
                                                                    ▼
+---------------+     +-----------------------+     +-------------------------------+
| Final Answer  | <-- |     LLM Generator     | <-- | Augmented Prompt:             |
| with Citation |     |  (Grounded Response)  |     | Context + Query + Rules       |
+---------------+     +-----------------------+     +-------------------------------+
```

### 1.2 End-to-End RAG Workflow
An end-to-end RAG architecture consists of two interconnected workflows: the **Offline Ingestion Pipeline** and the **Online Retrieval Pipeline**.

#### Phase A: Ingestion Pipeline (Data Preparation)
1. **Document Loading**: Ingest raw source files across formats (PDF, DOCX, TXT, CSV).
2. **Text Extraction & Normalization**: Strip binary headers, tags, non-printable characters, and redundant whitespace.
3. **Chunking**: Segment large documents into cohesive textual units (e.g., 300 to 500 characters) with a sliding window overlap (e.g., 50 to 100 characters).
4. **Embedding Generation**: Pass each text chunk through an embedding model (such as `all-MiniLM-L6-v2`) to produce a dense numerical vector representation (384 floating-point numbers).
5. **Storage & Indexing**: Save the raw chunk text and metadata (source file, chunk index, timestamp) into a relational database (SQLite), and index the vector embeddings into a vector matrix for mathematical comparison.

#### Phase B: Retrieval & Resolution Pipeline (Query Execution)
1. **Query Processing**: Clean and validate the user query.
2. **Query Vectorization**: Convert the query text into a vector using the identical embedding model used during ingestion.
3. **Similarity Search**: Calculate the mathematical distance (Cosine Similarity) between the query vector and every chunk vector in the index.
4. **Ranking & Thresholding**: Sort chunks by similarity score, filter out low-relevance matches below a confidence threshold, and select the Top-$K$ best chunks.
5. **Context Assembly**: Construct an augmented prompt containing the selected chunks and the user's question.
6. **Response Generation**: Deliver the augmented prompt to the generation engine (in future milestones) to synthesize a grounded answer.

### 1.3 Key Benefits and Inherent Limitations

#### Advantages
- **Grounding and Hallucination Reduction**: Responses are constrained to verifiable documents.
- **Dynamic Updates**: Updating knowledge requires only re-indexing a document, rather than expensive fine-tuning.
- **Auditability**: Every assertion in the response can cite the exact document and chunk ID it was drawn from.
- **Access Control & Privacy**: Documents can be restricted or tagged with permissions before retrieval.

#### Limitations
- **Retrieval Bottleneck**: If the retrieval engine selects irrelevant chunks, the generator will either fail to answer or generate an inaccurate response.
- **Context Window Limits**: Even modern LLMs with large context windows experience degradation in attention when flooded with loosely relevant text chunks.
- **Tabular Data Fragility**: Unstructured vector search struggles with complex quantitative calculations across tables without structured pre-processing.

---

## 2. Multi-Agent Query Resolution & Orchestration

### 2.1 The Need for Multi-Agent Systems
Monolithic RAG systems (a single prompt doing retrieval + reasoning + formatting) break down when faced with complex, multi-part, or ambiguous user queries. Multi-agent systems decompose the problem into specialized, autonomous units where each agent has a single, well-defined responsibility.

### 2.2 Roles of the 5 Specialized Agents

```
                         +-----------------------------------+
                         |       User Input / Voice          |
                         +-----------------------------------+
                                           │
                                           ▼
                         +-----------------------------------+
                         |   1. Query Understanding Agent    |
                         |   (Intent, Entities, Expansion)   |
                         +-----------------------------------+
                                    │             │
                [Ambiguous Query]   │             │  [Valid Query]
                                    ▼             ▼
+-----------------------------------+     +-----------------------------------+
|     4. Clarification Agent        |     |       2. Retrieval Agent          |
|  (Ask follow-ups, detect gaps)    |     |  (Semantic Search, Re-ranking)    |
+-----------------------------------+     +-----------------------------------+
                                                          │
                                                          ▼
+-----------------------------------+     +-----------------------------------+
|   5. Conversation Memory Agent    | <─> |   3. Response Generation Agent    |
| (Session context, user history)   |     | (Prompt Synthesis, Citations)     |
+-----------------------------------+     +-----------------------------------+
                                                          │
                                                          ▼
                                          +-----------------------------------+
                                          |    Final Answer to User / TTS     |
                                          +-----------------------------------+
```

#### 1. Query Understanding Agent
- **Responsibility**: Analyzes raw input, identifies user intent (informational, comparative, procedural), extracts key entities, and reformulates or expands short queries into semantically rich search terms.
- **Example**: If the user asks *"How do I restart it?"*, this agent consults conversation history to rewrite the query into *"Procedure for restarting Kubernetes worker nodes"*.

#### 2. Retrieval Agent
- **Responsibility**: Coordinates semantic search against the vector index and metadata database. Applies score thresholds, deduplicates overlapping passages, and sorts chunks to supply only high-quality context.

#### 3. Response Generation Agent
- **Responsibility**: Takes the retrieved context chunks and the user's query, formats the system prompt, instructs the LLM to adhere strictly to the context, and injects inline source citations (e.g., `[Doc: Deployment_Guide.docx, Chunk: 3]`).

#### 4. Clarification Agent
- **Responsibility**: Triggers when retrieval confidence is low, when the user query is intrinsically ambiguous, or when crucial information is missing. Rather than generating an ungrounded answer, it prompts the user with clarifying options.

#### 5. Conversation Memory Agent
- **Responsibility**: Maintains conversation session state, tracks multi-turn query history, and ensures that follow-up questions retain contextual continuity across the dialogue.

### 2.3 Orchestration Topologies and Information Flow
To coordinate these agents efficiently, three primary orchestration patterns exist:
1. **Sequential Pipeline**: Data flows in a linear chain ($Agent_1 \rightarrow Agent_2 \rightarrow Agent_3$). Simple to implement, but rigid.
2. **Conditional Router**: A central dispatcher evaluates the output of an agent and routes execution along different branches (e.g., if ambiguity score > 0.6, route to Clarification Agent; else route to Retrieval Agent).
3. **Evaluator-Optimizer Loop**: An agent generates a draft response, and an evaluation agent critiques the response for groundedness. If citations are missing or hallucinations are detected, it loops back for re-retrieval.

*For our architecture, we adopt a **Conditional Router topology** for Milestone 1 design, keeping the logic deterministic, testable, and beginner-friendly.*

---

## 3. Semantic Similarity and Vector Embeddings

### 3.1 Understanding Vector Embeddings
Computers do not inherently understand the meaning of words; they only see sequences of characters. A **vector embedding** is a mathematical translation of text into an array of floating-point numbers in an $n$-dimensional space.

Models trained on large corpora (such as Sentence-BERT and MiniLM) place semantically similar sentences close together in this vector space:
- *"The physician examined the patient."*
- *"A doctor checked on the sick person."*

Even though these two sentences share few identical words, their vector embeddings point in very similar directions in 384-dimensional space.

### 3.2 High-Dimensional Embedding Spaces
In our system, we use the `all-MiniLM-L6-v2` model:
- **Dimensions ($D$)**: 384 floating-point numbers per vector.
- **Normalized Length**: Vectors produced by Sentence-Transformers are unit-normalized such that their Euclidean norm equals 1:
  $$\|\vec{u}\| = \sqrt{\sum_{i=1}^{384} u_i^2} = 1.0$$
- **Dense Representation**: Unlike sparse representations (e.g., TF-IDF or Bag of Words where 99% of values are zero), dense vectors store meaningful floating-point weights across all 384 dimensions.

### 3.3 Similarity Metrics

When comparing a query vector $\vec{q}$ with a chunk vector $\vec{d}$, three primary mathematical distance metrics can be used:

```
          Cosine Similarity                       Euclidean Distance
           (Angle-focused)                         (Distance-focused)

                ▲   Query Vector                         ▲
                │   /                                    │      Query Vector (q)
                │  /                                     │      *
                │ / θ (Angle)                            │     /
                │/_________► Chunk Vector                │    / Euclidean Distance
                │                                        │   /  ||q - d||
                │                                        │  *
                │                                        │ Chunk Vector (d)
                └────────────────────────►               └────────────────────────►
```

#### 1. Cosine Similarity (Chosen Metric)
Measures the cosine of the angle $\theta$ between two vectors, regardless of their magnitude:
$$\text{Cosine Similarity}(\vec{q}, \vec{d}) = \frac{\vec{q} \cdot \vec{d}}{\|\vec{q}\| \|\vec{d}\|} = \frac{\sum_{i=1}^{n} q_i d_i}{\sqrt{\sum_{i=1}^{n} q_i^2} \sqrt{\sum_{i=1}^{n} d_i^2}}$$

- **Range**: $-1.0$ (opposite) to $+1.0$ (identical direction). In text embeddings, values typically fall between $0.0$ and $1.0$.
- **Why chosen**: Since our vectors are unit-normalized ($\|\vec{q}\| = \|\vec{d}\| = 1$), the denominator is $1.0$, and Cosine Similarity simplifies to a fast, vectorized dot product:
  $$\text{Cosine Similarity}(\vec{q}, \vec{d}) = \vec{q} \cdot \vec{d} = \sum_{i=1}^{384} q_i d_i$$

#### 2. Dot Product (Inner Product)
$$\vec{q} \cdot \vec{d} = \sum_{i=1}^{n} q_i d_i$$
- When vectors are unit-normalized, Dot Product is mathematically identical to Cosine Similarity. If vectors are unnormalized, longer texts can artificially inflate the score.

#### 3. Euclidean Distance ($L_2$ Distance)
Measures the straight-line geometric distance between two points:
$$d(\vec{q}, \vec{d}) = \sqrt{\sum_{i=1}^{n} (q_i - d_i)^2}$$
- **Range**: $0.0$ (identical) to $+\infty$. Smaller numbers represent closer proximity.

---

## 4. Document Chunking and Vector Search

### 4.1 The Importance of Document Chunking
Embedding an entire large document into a single 384-dimensional vector causes **information dilution**: the vector becomes an overly generic average of all topics in the document, losing fine-grained details. 

Chunking divides documents into coherent, focused passages that:
1. Fit within embedding model context limits (typically 256 or 512 tokens).
2. Allow precise pinpointing of specific paragraphs when retrieving answers.
3. Fit within LLM generation prompts alongside other retrieved passages.

### 4.2 Chunking Strategies & Overlap Rationale

| Strategy | Description | Best Suited For | Trade-offs |
| :--- | :--- | :--- | :--- |
| **Fixed-Size Chunking** | Splits text strictly every $N$ characters or words. | Baseline tests, uniform documents | Can split sentences or words in half |
| **Sentence-Aware Sliding Window** | Splits text by sentence boundaries into chunks of size $S$, sliding by overlap $O$. | **General RAG, technical manuals, policies (Our Choice)** | Slightly more compute during preprocessing |
| **Recursive Character Splitting** | Attempts splits by paragraphs (`\n\n`), then lines (`\n`), then spaces (` `). | Highly nested documents, markdown, code | Variable chunk sizes |
| **Semantic / Document Structure Chunking**| Splits based on section headings (`#`, `##`), table boundaries, or topic transitions. | Formal legal contracts, API docs | Complex parsing; format-dependent |

#### The Role of Chunk Overlap
If a crucial fact spans across the boundary between two chunks, splitting without overlap cuts the thought in half:
```
Chunk 1: "...to configure the failover cluster, the administrator must first issue the command"
Chunk 2: "cluster-init --primary. Failure to do so will cause immediate database downtime..."
```
Neither chunk contains the complete operational instruction. 

By applying an **overlap of 50 to 100 characters**, Chunk 2 repeats the end of Chunk 1, preserving semantic continuity across chunk borders.

### 4.3 Vector Indexing and Search Algorithms

#### 1. Flat Exact Search (Brute-Force / NumPy Index)
- **Mechanism**: Computes the exact cosine similarity between the query vector and every chunk vector in the database using matrix multiplication:
  $$\mathbf{S} = \mathbf{Q} \cdot \mathbf{D}^T$$
- **Pros**: **100% recall** (guaranteed to find the true mathematical nearest neighbors); zero index build time; simple and transparent for beginners; zero external dependencies.
- **Cons**: Computational complexity is $\mathcal{O}(N \cdot D)$. For very large document corpuses with millions of chunks, search latency grows linearly.
- **Selection for Milestone 1**: For small-to-medium educational collections in Milestone 1, NumPy flat exact search provides immediate execution, beginner-friendly clarity, and zero black-box setup.

#### 2. Approximate Nearest Neighbors (ANN) (Future Milestones)
- **IVFFlat (Inverted File Flat)**: Clusters vectors into Voronoi cells and searches only within the nearest centroids.
- **HNSW (Hierarchical Navigable Small World)**: Builds a multi-layer graph where greedy routing converges on nearest neighbors in $\mathcal{O}(\log N)$ time. Used in production vector databases (Chroma, FAISS, Milvus, Qdrant).

---

## 5. Web Speech API: Speech-to-Text & Text-to-Speech

### 5.1 Overview and Browser Architecture
The **Web Speech API** is a standardized W3C browser interface that allows web applications to incorporate voice data without requiring custom audio recording backends or native binaries.

It consists of two independent interfaces:
1. `SpeechRecognition`: Converts user speech from a microphone into real-time text (Speech-to-Text / STT).
2. `SpeechSynthesis`: Converts textual strings into spoken synthesized audio through computer speakers (Text-to-Speech / TTS).

```
   [User Speaks into Mic]                     [Platform Reads Answer]
             │                                           ▲
             ▼                                           │
+───────────────────────────+               +───────────────────────────+
|     SpeechRecognition     |               |      SpeechSynthesis      |
|  (Audio Buffer -> Text)   |               |   (Text -> Audio Stream)  |
+───────────────────────────+               +───────────────────────────+
             │                                           ▲
             ▼                                           │
     Captured Query String                       Generated Response
             │                                           │
             └────────► [ RAG Retrieval Pipeline ] ──────┘
```

### 5.2 SpeechRecognition (Speech-to-Text / STT)

#### Working Principle & Event Cycle
1. The web application instantiates `const recognition = new webkitSpeechRecognition() || new SpeechRecognition()`.
2. The user grants microphone permissions via standard browser prompts.
3. The browser streams audio to the underlying speech recognition engine.
4. As speech occurs, the engine fires JavaScript events:
   - `onstart`: Audio capture has begun.
   - `onspeechstart`: Speech detected.
   - `onresult`: Text transcription returned. Can return interim (in-progress) and final results with confidence scores ($0.0$ to $1.0$).
   - `onerror`: Captures permission denials, network failures, or silence timeouts.
   - `onend`: Audio capture stopped.

### 5.3 SpeechSynthesis (Text-to-Speech / TTS)

#### Working Principle
1. The application constructs an utterance object: `const utterance = new SpeechSynthesisUtterance("Response text")`.
2. Parameters are configured:
   - `utterance.voice`: Selected from `window.speechSynthesis.getVoices()`.
   - `utterance.rate`: Speed multiplier ($0.1$ to $10$, default $1.0$).
   - `utterance.pitch`: Pitch multiplier ($0$ to $2$, default $1.0$).
   - `utterance.volume`: Loudness ($0$ to $1$).
3. The browser invokes `window.speechSynthesis.speak(utterance)`.

### 5.4 Advantages, Limitations, and Fallbacks

#### Advantages
- **Zero Server Costs**: Speech processing runs client-side or through the browser's built-in provider.
- **Low Transfer Overhead**: Audio is processed directly in the client rather than uploaded across HTTP.
- **Accessibility**: Hands-free voice querying for users with accessibility needs.

#### Limitations
- **Browser Inconsistency**: Full `SpeechRecognition` is supported natively in Chrome, Edge, and Safari, but has limited support in Firefox.
- **Network Dependency in Chromium**: Chrome routes audio buffers through Google's speech servers; if the client is completely offline, recognition may fail unless local OS speech packs are installed.
- **Background Noise**: Recognition accuracy drops in noisy environments.

#### Proposed Architecture & Fallback Strategy
In our platform design:
- Voice is an **optional input enhancement**, never a hard requirement.
- The UI checks for `window.SpeechRecognition || window.webkitSpeechRecognition`. If unavailable, the microphone button is gracefully disabled with a helpful tooltip, allowing standard keyboard text input.
- Text output is always displayed visually on screen, with an optional "Read Aloud" button triggering `SpeechSynthesis`.

---

## 6. Architectural Decisions & Technical Reasoning

| Decision Point | Selection for Milestone 1 | Alternatives Considered | Technical Reasoning |
| :--- | :--- | :--- | :--- |
| **Backend Language** | **Python 3.14** | Node.js, Go, Rust | Python is the uncontested standard for AI/ML and NLP, featuring native libraries for embeddings and numerical manipulation. |
| **Backend Framework** | **FastAPI** | Flask, Django, Express | FastAPI offers asynchronous endpoints, automatic Pydantic request validation, and built-in interactive Swagger documentation (`/docs`), which is invaluable for a beginner developer. |
| **Document Parsers** | **`pypdf`, `python-docx`, `pandas`** | `pdfplumber`, `unstructured`, `Tesseract` | `pypdf` and `python-docx` are pure Python or lightweight binary wheels without complex C/C++ compile chains or external system binaries (like Poppler). `pandas` excels at tabular CSV restructuring. |
| **Embedding Model** | **`all-MiniLM-L6-v2` (Sentence-Transformers)** | OpenAI `text-embedding-3-small`, Cohere, BERT-base | Runs completely locally on CPU (~80MB download); no API keys, billing accounts, or internet calls required during inference; 384 dimensions provide high semantic accuracy. |
| **Vector Storage** | **In-Memory NumPy Matrix + SQLite Persistence** | ChromaDB, Pinecone, FAISS, Weaviate | Keeps the codebase 100% transparent and educational. Beginners can directly inspect how dot products and cosine similarity matrices work without treating vector databases as "magic black boxes". |
| **Metadata Storage** | **SQLite (`sqlite3`)** | PostgreSQL, MongoDB | Serverless, zero-configuration, built directly into Python standard library, reliable ACID compliance. |
| **Testing Suite** | **`pytest`** | `unittest` | Expressive assertions, clear failure diffs, simple test discovery. |

---

## 7. Technical References and Documentation Links

1. **Retrieval-Augmented Generation (Foundational Paper)**:
   - Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. Advances in Neural Information Processing Systems (NeurIPS 2020). [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
2. **Sentence-Transformers & MiniLM**:
   - Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019. [https://arxiv.org/abs/1908.10084](https://arxiv.org/abs/1908.10084)
   - Hugging Face Model Card: `sentence-transformers/all-MiniLM-L6-v2`. [https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
   - Sentence-Transformers Official Documentation: [https://sbert.net/](https://sbert.net/)
3. **Document Parsers**:
   - `pypdf` Official Documentation: [https://pypdf.readthedocs.io/](https://pypdf.readthedocs.io/)
   - `python-docx` Official Documentation: [https://python-docx.readthedocs.io/](https://python-docx.readthedocs.io/)
   - `pandas` User Guide: [https://pandas.pydata.org/docs/user_guide/index.html](https://pandas.pydata.org/docs/user_guide/index.html)
4. **FastAPI & Uvicorn**:
   - FastAPI Documentation: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
   - Starlette Toolkit: [https://www.starlette.io/](https://www.starlette.io/)
5. **Web Speech API (W3C Specification)**:
   - W3C Community Group Specification: [https://wicg.github.io/speech-api/](https://wicg.github.io/speech-api/)
   - MDN Web Docs: Web Speech API: [https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
   - MDN Web Docs: SpeechRecognition: [https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
   - MDN Web Docs: SpeechSynthesis: [https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)
6. **Vector Search Mathematics & NumPy**:
   - NumPy Linear Algebra & Matrix Routines: [https://numpy.org/doc/stable/reference/routines.linalg.html](https://numpy.org/doc/stable/reference/routines.linalg.html)
   - Cosine Similarity & Vector Norms: [https://en.wikipedia.org/wiki/Cosine_similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
