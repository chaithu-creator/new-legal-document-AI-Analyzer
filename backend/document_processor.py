import re
import io
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF bytes."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text("text"))
    doc.close()
    raw_text = "\n".join(text_parts)
    return _clean_text(raw_text)


def _clean_text(text: str) -> str:
    """Remove noise and normalize whitespace."""
    # Remove excessive whitespace while preserving paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove page numbers patterns like "Page 1 of 10"
    text = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "", text)
    # Remove repeated dashes / underscores used as dividers
    text = re.sub(r"[-_]{3,}", "", text)
    return text.strip()


def detect_document_type(text: str) -> str:
    """Detect whether document is a legal contract or a land document."""
    land_keywords = [
        "survey number", "survey no", "plot number", "plot no",
        "sale deed", "encumbrance", "patta", "khata", "khasra",
        "land area", "sq.ft", "acres", "registration number",
        "sub-registrar", "ec certificate", "property address",
        "owner name", "vendor", "vendee", "revenue",
    ]
    contract_keywords = [
        "agreement", "contract", "parties", "clause", "termination",
        "liability", "indemnity", "confidentiality", "penalty",
        "arbitration", "governing law", "breach", "warranty",
    ]
    text_lower = text.lower()
    land_score = sum(1 for kw in land_keywords if kw in text_lower)
    contract_score = sum(1 for kw in contract_keywords if kw in text_lower)

    if land_score >= contract_score and land_score > 2:
        return "land"
    return "contract"
