"""
Text extraction — one function per file type, all returning plain text.
"""

import csv
import io

from fastapi import UploadFile
from pypdf import PdfReader
from docx import Document as DocxDocument


async def extract_text(file: UploadFile) -> str:
    """Dispatch to the correct extractor based on file extension."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()

    extractors = {
        "pdf": _extract_pdf,
        "docx": _extract_docx,
        "csv": _extract_csv,
        "txt": _extract_txt,
    }

    extractor = extractors.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported file type: .{ext}. Supported: pdf, docx, csv, txt")

    return extractor(content)


def _extract_pdf(content: bytes) -> str:
    """Extract text from all pages of a PDF."""
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def _extract_docx(content: bytes) -> str:
    """Extract text from all paragraphs of a DOCX."""
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs).strip()


def _extract_csv(content: bytes) -> str:
    """Flatten CSV rows into readable lines (col1: val1, col2: val2 per row).
    This format reads better for embeddings than raw CSV."""
    text_content = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text_content))
    rows = list(reader)

    if len(rows) < 2:
        return text_content.strip()

    headers = rows[0]
    lines = []
    for row in rows[1:]:
        pairs = [f"{h}: {v}" for h, v in zip(headers, row) if v.strip()]
        lines.append(", ".join(pairs))

    return "\n".join(lines).strip()


def _extract_txt(content: bytes) -> str:
    """Read plain text as-is."""
    return content.decode("utf-8", errors="replace").strip()
