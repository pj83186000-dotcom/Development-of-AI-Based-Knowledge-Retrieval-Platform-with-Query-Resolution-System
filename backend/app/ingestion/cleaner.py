"""Text cleaning and normalization module.

Implements Unicode NFKC normalization, whitespace standardization, control character
removal, and hyphenation break repair.
"""

import re
import unicodedata


def clean_text(raw_text: str) -> str:
    """Clean and normalize raw extracted document text.
    
    Processing steps:
    1. Unicode NFKC normalization.
    2. Repair hyphenated word breaks across newlines (e.g., 'micro-\nservice' -> 'microservice').
    3. Filter non-printable control characters (retaining standard whitespace: newline, tab, space).
    4. Collapse multiple horizontal whitespace characters (spaces/tabs) into a single space.
    5. Standardize vertical whitespace: limit consecutive newlines to at most two (\n\n).
    6. Strip leading and trailing whitespace.
    """
    if not raw_text:
        return ""
    
    # 1. Unicode normalization (NFKC decomposes compatibility characters and composes canonically)
    normalized = unicodedata.normalize("NFKC", raw_text)
    
    # 2. Repair hyphenated word breaks across line wraps
    # e.g., 'configu-\nration' -> 'configuration'
    repaired = re.sub(r"(\b[A-Za-z]+)-\s*\n\s*([A-Za-z]+\b)", r"\1\2", normalized)
    
    # 3. Filter out non-printable ASCII / control characters (keep \n, \t, \r, and printable chars)
    # Characters in category 'Cc' (other, control) except \n (10), \t (9), \r (13)
    filtered_chars = [
        ch for ch in repaired
        if not unicodedata.category(ch).startswith("C") or ch in "\n\t\r"
    ]
    cleaned = "".join(filtered_chars)
    
    # Standardize carriage returns to standard newlines
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    
    # 4. Collapse horizontal whitespace (multiple spaces and tabs on the same line)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    
    # Clean spaces around line breaks
    cleaned = re.sub(r" ?\n ?", "\n", cleaned)
    
    # 5. Limit consecutive newlines to at most two (\n\n) to preserve paragraph structure
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    
    # 6. Final strip
    return cleaned.strip()

