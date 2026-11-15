"""Document extractors for PDF, DOCX, TXT, and CSV file formats.

Implements format-specific parsing with error handling, metadata tracking,
and multi-encoding fallback.
"""

import io
from typing import Any, Dict, Tuple
import pandas as pd
import pypdf
import docx

from backend.app.database.models import FileType


def extract_pdf(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text and metadata from a PDF file using pypdf.
    
    Returns (extracted_text, metadata_dict).
    Raises ValueError if extraction fails or PDF is corrupted.
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)
        if num_pages == 0:
            raise ValueError("PDF contains 0 pages.")
        
        page_texts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            page_texts.append(text)
        
        full_text = "\n\n".join(t for t in page_texts if t.strip())
        if not full_text.strip():
            raise ValueError("PDF contains no extractable text.")
        
        metadata = {
            "format": "pdf",
            "page_count": num_pages,
            "extracted_pages": len(page_texts),
        }
        return full_text, metadata
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to extract text from PDF: {str(e)}") from e


def extract_docx(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text and metadata from a DOCX file using python-docx.
    
    Extracts text from paragraphs and tables.
    Returns (extracted_text, metadata_dict).
    Raises ValueError if extraction fails or DOCX contains no text.
    """
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text_elements = []
        
        # 1. Paragraphs
        paragraph_count = 0
        for p in doc.paragraphs:
            content = p.text.strip()
            if content:
                text_elements.append(content)
                paragraph_count += 1
        
        # 2. Tables
        table_count = 0
        table_cell_texts = []
        for table in doc.tables:
            table_count += 1
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    # Remove consecutive duplicates in merged cells
                    unique_cells = []
                    for c in row_cells:
                        if not unique_cells or unique_cells[-1] != c:
                            unique_cells.append(c)
                    table_cell_texts.append(" | ".join(unique_cells))
        
        if table_cell_texts:
            text_elements.extend(table_cell_texts)
        
        full_text = "\n\n".join(text_elements)
        if not full_text.strip():
            raise ValueError("DOCX contains no extractable text.")
        
        metadata = {
            "format": "docx",
            "paragraph_count": paragraph_count,
            "table_count": table_count,
        }
        return full_text, metadata
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}") from e


def extract_txt(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a plain text file using UTF-8 -> CP1252 -> Latin-1 fallback.
    
    Latin-1 is the final fallback because it maps all 256 byte values (0x00-0xFF)
    to Unicode and never fails with UnicodeDecodeError, preventing CP1252 detection
    if placed earlier.
    
    Returns (extracted_text, metadata_dict).
    Raises ValueError if text is empty or decode fails.
    """
    encodings = ["utf-8", "cp1252", "latin-1"]
    decoded_text = None
    used_encoding = None
    
    for enc in encodings:
        try:
            decoded_text = file_bytes.decode(enc)
            used_encoding = enc
            break
        except UnicodeDecodeError:
            continue
    
    if decoded_text is None:
        raise ValueError("Failed to decode text file with UTF-8, CP1252, or Latin-1.")
    
    if not decoded_text.strip():
        raise ValueError("Text file contains no text content.")
    
    metadata = {
        "format": "txt",
        "encoding": used_encoding,
    }
    return decoded_text, metadata


def extract_csv(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract and serialize tabular data from a CSV file using pandas.
    
    Converts each row into a structured, readable sentence to optimize
    semantic embedding quality.
    
    Returns (extracted_text, metadata_dict).
    Raises ValueError if CSV is empty or cannot be parsed.
    """
    try:
        # Try UTF-8 then fallback to Latin-1
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
        
        if df.empty:
            raise ValueError("CSV file contains no data rows.")
        
        num_rows, num_cols = df.shape
        columns = list(df.columns)
        
        sentences = []
        for idx, row in df.iterrows():
            parts = [f"{col}: {row[col]}" for col in columns if pd.notna(row[col])]
            if parts:
                sentences.append(f"Row {idx + 1} - " + "; ".join(parts) + ".")
        
        full_text = "\n".join(sentences)
        if not full_text.strip():
            raise ValueError("CSV contains no non-empty rows.")
        
        metadata = {
            "format": "csv",
            "row_count": num_rows,
            "column_count": num_cols,
            "columns": columns,
        }
        return full_text, metadata
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse CSV file: {str(e)}") from e


def extract_document(
    file_bytes: bytes, file_type: FileType
) -> Tuple[str, Dict[str, Any]]:
    """Route document bytes to the corresponding extractor based on file type."""
    if file_type == FileType.PDF:
        return extract_pdf(file_bytes)
    elif file_type == FileType.DOCX:
        return extract_docx(file_bytes)
    elif file_type == FileType.TXT:
        return extract_txt(file_bytes)
    elif file_type == FileType.CSV:
        return extract_csv(file_bytes)
    else:
        raise ValueError(f"No extractor available for file type '{file_type}'.")

