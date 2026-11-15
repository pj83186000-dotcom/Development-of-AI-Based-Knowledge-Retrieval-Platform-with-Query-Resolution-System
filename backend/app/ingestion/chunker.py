"""Sentence-aware sliding window text chunker.

Produces overlapping chunks with exact offset tracking, satisfying all
Pydantic and SQLite length and offset constraints.
"""

from typing import Any, Dict, List
from backend.app.database.models import Chunk
from backend.app.ingestion.validators import generate_chunk_id

DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 80


def estimate_token_count(text: str) -> int:
    """Estimate token count based on whitespace word count multiplied by 1.3."""
    words = text.split()
    if not words:
        return 1
    return max(1, int(len(words) * 1.3))


def chunk_text(
    cleaned_text: str,
    document_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    base_metadata: Dict[str, Any] = None,
) -> List[Chunk]:
    """Segment cleaned text into overlapping Chunk models with precise character offsets.
    
    Guarantees:
    - end_char > start_char
    - char_length == (end_char - start_char) == len(text)
    - token_count >= 1
    
    Args:
        cleaned_text: Normalized document text string.
        document_id: Parent document identifier.
        chunk_size: Target character length per chunk (default 400).
        chunk_overlap: Overlapping characters between adjacent chunks (default 80).
        base_metadata: Optional dictionary with format-specific metadata.
    
    Returns:
        List of validated Chunk models.
    """
    if not cleaned_text or not cleaned_text.strip():
        return []
    
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )
    
    n = len(cleaned_text)
    chunks: List[Chunk] = []
    start = 0
    chunk_index = 0
    
    while start < n:
        # Advance past leading whitespace to preserve clean text boundaries
        while start < n and cleaned_text[start].isspace():
            start += 1
        if start >= n:
            break
        
        target_end = min(start + chunk_size, n)
        if target_end < n:
            # 1. Search for sentence punctuation boundaries within the target window
            sentence_break = -1
            for punct in (". ", "? ", "! ", ".\n", "?\n", "!\n"):
                pos = cleaned_text.rfind(punct, start + int(chunk_size * 0.4), target_end)
                if pos > sentence_break:
                    sentence_break = pos + len(punct) - 1  # Include the punctuation mark
            
            if sentence_break != -1:
                end = sentence_break
            else:
                # 2. Search for word space boundary
                space_break = cleaned_text.rfind(" ", start + int(chunk_size * 0.3), target_end)
                if space_break != -1:
                    end = space_break
                else:
                    # 3. Fallback to hard slice
                    end = target_end
        else:
            end = n
        
        # Trim trailing whitespace from end to preserve strict length equality
        while end > start and cleaned_text[end - 1].isspace():
            end -= 1
        
        if end > start:
            slice_text = cleaned_text[start:end]
            char_length = end - start
            tokens = estimate_token_count(slice_text)
            
            chunk_meta = dict(base_metadata or {})
            chunk_meta["chunk_size_target"] = chunk_size
            chunk_meta["chunk_overlap_target"] = chunk_overlap
            
            chunk_obj = Chunk(
                id=generate_chunk_id(),
                document_id=document_id,
                chunk_index=chunk_index,
                text=slice_text,
                char_length=char_length,
                token_count=tokens,
                start_char=start,
                end_char=end,
                metadata=chunk_meta,
            )
            chunks.append(chunk_obj)
            chunk_index += 1
        
        if end >= n:
            break
        
        # Calculate next starting position with overlap
        next_start = max(start + 1, end - chunk_overlap)
        start = next_start
    
    return chunks

