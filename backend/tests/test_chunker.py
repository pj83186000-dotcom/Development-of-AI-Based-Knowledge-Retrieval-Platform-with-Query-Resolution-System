"""Unit tests for sentence-aware sliding window text chunking."""

import pytest
from backend.app.ingestion.chunker import chunk_text, estimate_token_count


def test_estimate_token_count():
    assert estimate_token_count("") == 1
    assert estimate_token_count("Hello world") == max(1, int(2 * 1.3))


def test_chunk_text_empty():
    assert chunk_text("", "doc_123") == []
    assert chunk_text("   \n  ", "doc_123") == []


def test_chunk_text_short():
    text = "A concise sentence describing container virtualization."
    chunks = chunk_text(text, "doc_123", chunk_size=400, chunk_overlap=80)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_id == "doc_123"
    assert c.chunk_index == 0
    assert c.text == text
    assert c.char_length == len(text)
    assert c.start_char == 0
    assert c.end_char == len(text)
    assert c.token_count >= 1


def test_chunk_text_long_sliding_window():
    # Long text with multiple sentences
    sentences = [
        f"Sentence number {i} provides detailed contextual explanation for DevOps engineering."
        for i in range(25)
    ]
    text = " ".join(sentences)
    chunk_size = 350
    overlap = 70
    
    chunks = chunk_text(text, "doc_456", chunk_size=chunk_size, chunk_overlap=overlap)
    assert len(chunks) > 1
    
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.document_id == "doc_456"
        assert c.char_length == (c.end_char - c.start_char)
        assert c.char_length == len(c.text)
        assert c.end_char > c.start_char
        assert c.token_count >= 1
        
        # Verify text slice matches parent text
        assert text[c.start_char:c.end_char] == c.text


def test_chunk_text_invalid_overlap():
    with pytest.raises(ValueError, match="must be strictly less than chunk_size"):
        chunk_text("Sample text", "doc_123", chunk_size=100, chunk_overlap=100)
    with pytest.raises(ValueError, match="must be strictly less than chunk_size"):
        chunk_text("Sample text", "doc_123", chunk_size=100, chunk_overlap=120)

