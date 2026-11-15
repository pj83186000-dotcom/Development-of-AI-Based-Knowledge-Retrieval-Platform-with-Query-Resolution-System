"""
Script to generate publication-grade multi-page PDF documents from Markdown specifications.
Produces:
1. documentation/system_architecture.pdf
2. documentation/technology_stack.pdf
"""

import os
import re
from pathlib import Path
import pypdf


def sanitize_text(text: str) -> str:
    """Normalize unicode characters to ASCII/Latin-1 safe equivalents."""
    replacements = {
        "—": " -- ",
        "–": " - ",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "*",
        "→": "->",
        "←": "<-",
        "↔": "<->",
        "≥": ">=",
        "≤": "<=",
        "±": "+/-",
        "·": "*",
        "✓": "[x]",
        "✅": "[PASS]",
        "⏳": "[PENDING]",
        "❌": "[FAIL]",
        "…": "...",
        "\u00a0": " ",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Filter to printable ASCII
    return "".join(c if ord(c) < 128 else " " for c in text)


def escape_pdf_literal(text: str) -> str:
    """Escape backslashes and parentheses for PDF string literals."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text: str, max_chars: int = 85) -> list:
    """Wrap plain text lines to fit page margins."""
    words = text.split()
    if not words:
        return []
    lines = []
    current = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 > max_chars:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += len(w) + (1 if current_len > 0 else 0)
    if current:
        lines.append(" ".join(current))
    return lines


class SimplePDFWriter:
    def __init__(self, title: str):
        self.title = title
        self.pages = []
        self.current_page_ops = []
        self.y = 730  # start near top
        self.min_y = 55
        self.page_width = 612
        self.page_height = 792
        self.margin_x = 54

    def _flush_page(self):
        if self.current_page_ops:
            self.pages.append(self.current_page_ops)
            self.current_page_ops = []
        self.y = 730

    def check_space(self, needed: int):
        if self.y - needed < self.min_y:
            self._flush_page()

    def add_title(self, text: str):
        self.check_space(50)
        safe = escape_pdf_literal(sanitize_text(text))
        self.current_page_ops.append(f"BT /F2 16 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
        self.y -= 22
        # Decorative rule
        self.current_page_ops.append(f"{self.margin_x} {self.y + 10} m {self.page_width - self.margin_x} {self.y + 10} l S")
        self.y -= 12

    def add_h1(self, text: str):
        self.check_space(40)
        self.y -= 8
        safe = escape_pdf_literal(sanitize_text(text))
        self.current_page_ops.append(f"BT /F2 13 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
        self.y -= 18

    def add_h2(self, text: str):
        self.check_space(32)
        self.y -= 6
        safe = escape_pdf_literal(sanitize_text(text))
        self.current_page_ops.append(f"BT /F2 11 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
        self.y -= 16

    def add_h3(self, text: str):
        self.check_space(26)
        self.y -= 4
        safe = escape_pdf_literal(sanitize_text(text))
        self.current_page_ops.append(f"BT /F2 9.5 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
        self.y -= 14

    def add_paragraph(self, text: str):
        sanitized = sanitize_text(text)
        lines = wrap_text(sanitized, max_chars=88)
        needed = len(lines) * 13 + 6
        self.check_space(needed)
        for line in lines:
            safe = escape_pdf_literal(line)
            self.current_page_ops.append(f"BT /F1 9 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
            self.y -= 13
        self.y -= 5

    def add_bullet(self, text: str):
        sanitized = sanitize_text(text)
        lines = wrap_text(sanitized, max_chars=84)
        needed = len(lines) * 13 + 4
        self.check_space(needed)
        bullet_drawn = False
        for line in lines:
            safe = escape_pdf_literal(line)
            if not bullet_drawn:
                self.current_page_ops.append(f"BT /F2 9 Tf {self.margin_x} {self.y} Td (*) Tj ET")
                self.current_page_ops.append(f"BT /F1 9 Tf {self.margin_x + 14} {self.y} Td ({safe}) Tj ET")
                bullet_drawn = True
            else:
                self.current_page_ops.append(f"BT /F1 9 Tf {self.margin_x + 14} {self.y} Td ({safe}) Tj ET")
            self.y -= 13
        self.y -= 3

    def add_code_line(self, text: str):
        self.check_space(12)
        safe = escape_pdf_literal(sanitize_text(text[:100]))
        self.current_page_ops.append(f"BT /F3 7.5 Tf {self.margin_x + 10} {self.y} Td ({safe}) Tj ET")
        self.y -= 10

    def add_table_row(self, cells: list):
        self.check_space(14)
        formatted = " | ".join(c.strip() for c in cells if c.strip())
        safe = escape_pdf_literal(sanitize_text(formatted[:105]))
        self.current_page_ops.append(f"BT /F3 7.5 Tf {self.margin_x} {self.y} Td ({safe}) Tj ET")
        self.y -= 12

    def build_pdf_bytes(self) -> bytes:
        if self.current_page_ops:
            self._flush_page()

        total_pages = len(self.pages)
        # Add footers (Page X of Y)
        for idx, p_ops in enumerate(self.pages, 1):
            footer_text = f"Page {idx} of {total_pages}  --  {self.title[:45]}"
            safe_footer = escape_pdf_literal(footer_text)
            p_ops.append(f"BT /F1 7.5 Tf {self.margin_x} 35 Td ({safe_footer}) Tj ET")
            p_ops.append(f"{self.margin_x} 45 m {self.page_width - self.margin_x} 45 l S")

        # PDF Object structure:
        # obj 1: Catalog
        # obj 2: Pages
        # obj 3.. 3+N-1: Page objects
        # obj 3+N.. 3+2N-1: Contents streams
        # obj font1: Helvetica
        # obj font2: Helvetica-Bold
        # obj font3: Courier
        num_pages = len(self.pages)
        catalog_id = 1
        pages_id = 2
        first_page_id = 3
        first_content_id = first_page_id + num_pages
        font1_id = first_content_id + num_pages
        font2_id = font1_id + 1
        font3_id = font2_id + 1

        objects = {}

        # 1. Catalog
        objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")

        # 2. Pages
        kids_refs = " ".join(f"{first_page_id + i} 0 R" for i in range(num_pages))
        objects[pages_id] = f"<< /Type /Pages /Kids [{kids_refs}] /Count {num_pages} >>".encode("ascii")

        # Fonts
        objects[font1_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objects[font2_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
        objects[font3_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"

        # Page and Content objects
        for i in range(num_pages):
            page_obj_id = first_page_id + i
            content_obj_id = first_content_id + i
            page_dict = (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 612 792] "
                f"/Contents {content_obj_id} 0 R "
                f"/Resources << /Font << /F1 {font1_id} 0 R /F2 {font2_id} 0 R /F3 {font3_id} 0 R >> >> >>"
            ).encode("ascii")
            objects[page_obj_id] = page_dict

            stream_data = "\n".join(self.pages[i]).encode("latin-1")
            content_dict = (
                f"<< /Length {len(stream_data)} >>\nstream\n".encode("ascii")
                + stream_data
                + b"\nendstream"
            )
            objects[content_obj_id] = content_dict

        # Assemble PDF file with correct xref offsets
        header = b"%PDF-1.4\n"
        body = bytearray(header)
        xref_table = {0: 0}

        sorted_ids = sorted(objects.keys())
        for oid in sorted_ids:
            xref_table[oid] = len(body)
            body += f"{oid} 0 obj\n".encode("ascii")
            body += objects[oid]
            body += b"\nendobj\n"

        xref_pos = len(body)
        total_objs = max(sorted_ids) + 1
        body += f"xref\n0 {total_objs}\n".encode("ascii")
        body += b"0000000000 65535 f \n"
        for oid in range(1, total_objs):
            pos = xref_table.get(oid, 0)
            body += f"{pos:010d} 00000 n \n".encode("ascii")

        body += f"trailer\n<< /Size {total_objs} /Root {catalog_id} 0 R >>\n".encode("ascii")
        body += b"startxref\n"
        body += f"{xref_pos}\n%%EOF\n".encode("ascii")

        return bytes(body)


def convert_markdown_to_pdf(md_path: Path, pdf_path: Path, doc_title: str):
    """Parse Markdown file and generate formatted PDF."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    writer = SimplePDFWriter(title=doc_title)
    writer.add_title(doc_title)

    lines = text.split("\n")
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            writer.add_code_line(line)
            continue

        if stripped.startswith("# "):
            pass  # Title already added
        elif stripped.startswith("## "):
            writer.add_h1(stripped[3:])
        elif stripped.startswith("### "):
            writer.add_h2(stripped[4:])
        elif stripped.startswith("#### "):
            writer.add_h3(stripped[5:])
        elif stripped.startswith("- ") or stripped.startswith("* "):
            writer.add_bullet(stripped[2:])
        elif re.match(r"^\d+\.\s+", stripped):
            writer.add_bullet(re.sub(r"^\d+\.\s+", "", stripped))
        elif stripped.startswith("|"):
            if "---" not in stripped:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                writer.add_table_row(cells)
        elif stripped.startswith(">"):
            writer.add_paragraph(stripped[1:].strip())
        else:
            writer.add_paragraph(stripped)

    pdf_bytes = writer.build_pdf_bytes()
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Verify generated PDF with pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    print(f"Generated '{pdf_path.name}': {len(reader.pages)} pages, {len(pdf_bytes)} bytes.")


if __name__ == "__main__":
    docs_dir = Path("documentation")
    
    # 1. System Architecture PDF
    arch_md = docs_dir / "system_architecture.md"
    arch_pdf = docs_dir / "system_architecture.pdf"
    convert_markdown_to_pdf(
        arch_md, arch_pdf, "System Architecture Specification"
    )

    # 2. Technology Stack PDF
    tech_md = docs_dir / "technology_stack.md"
    tech_pdf = docs_dir / "technology_stack.pdf"
    convert_markdown_to_pdf(
        tech_md, tech_pdf, "Technology Stack Specification"
    )
    print("PDF generation completed successfully!")
