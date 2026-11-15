-- ============================================================================
-- AI-Based Knowledge Retrieval Platform: Database DDL Schema
-- Database Engine: SQLite 3
-- Target Milestone: Milestone 1 & Beyond
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL CHECK(file_type IN ('pdf', 'docx', 'txt', 'csv')),
    file_size_bytes INTEGER NOT NULL CHECK(file_size_bytes > 0),
    file_hash VARCHAR(64) NOT NULL CHECK(length(file_hash) = 64),
    domain VARCHAR(50) NOT NULL DEFAULT 'general',
    chunk_count INTEGER NOT NULL DEFAULT 0 CHECK(chunk_count >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processed', 'failed')),
    upload_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain);

-- 2. Chunks Table
CREATE TABLE IF NOT EXISTS chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    chunk_index INTEGER NOT NULL CHECK(chunk_index >= 0),
    text TEXT NOT NULL,
    char_length INTEGER NOT NULL CHECK(char_length > 0),
    token_count INTEGER NOT NULL CHECK(token_count > 0),
    start_char INTEGER NOT NULL CHECK(start_char >= 0),
    end_char INTEGER NOT NULL CHECK(end_char > start_char),
    metadata_json TEXT DEFAULT '{}',
    CHECK(char_length = end_char - start_char),
    CHECK(char_length = length(text)),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(document_id, chunk_index);

-- 3. Embeddings Table
CREATE TABLE IF NOT EXISTS embeddings (
    id VARCHAR(64) PRIMARY KEY,
    chunk_id VARCHAR(64) NOT NULL UNIQUE,
    model_name VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    dimension INTEGER NOT NULL DEFAULT 384 CHECK(dimension = 384),
    vector_blob BLOB NOT NULL CHECK(length(vector_blob) = 1536),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);

-- 4. Queries Table
CREATE TABLE IF NOT EXISTS queries (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    raw_query_text TEXT NOT NULL,
    processed_query_text TEXT,
    query_type VARCHAR(20) NOT NULL DEFAULT 'factual' CHECK(query_type IN ('factual', 'procedural', 'comparative', 'unavailable', 'ambiguous')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_session_id ON queries(session_id);

-- 5. Retrieval Results Table
CREATE TABLE IF NOT EXISTS retrieval_results (
    id VARCHAR(64) PRIMARY KEY,
    query_id VARCHAR(64) NOT NULL,
    chunk_id VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    similarity_score REAL NOT NULL CHECK(similarity_score >= -1.0 AND similarity_score <= 1.0),
    rank INTEGER NOT NULL CHECK(rank >= 1),
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_retrieval_query_id ON retrieval_results(query_id);

-- 6. Responses Table
CREATE TABLE IF NOT EXISTS responses (
    id VARCHAR(64) PRIMARY KEY,
    query_id VARCHAR(64) NOT NULL UNIQUE,
    response_text TEXT NOT NULL,
    cited_chunk_ids TEXT DEFAULT '[]',
    confidence_score REAL NOT NULL CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
    status VARCHAR(20) NOT NULL DEFAULT 'answered' CHECK(status IN ('answered', 'clarified', 'unavailable')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_responses_query_id ON responses(query_id);

