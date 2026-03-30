import re
from typing import List, Dict

# Clause type keyword map
CLAUSE_LABELS = {
    "termination": [
        "terminat", "cancell", "end of agreement", "expiry", "notice period",
    ],
    "liability": [
        "liabilit", "liable", "indemnif", "damages", "loss", "harm",
    ],
    "payment": [
        "payment", "fee", "invoice", "compensation", "remuneration", "salary",
        "price", "cost", "amount due",
    ],
    "confidentiality": [
        "confidential", "non-disclosure", "nda", "proprietary", "secret",
    ],
    "intellectual_property": [
        "intellectual property", "copyright", "trademark", "patent", "ip rights",
    ],
    "dispute_resolution": [
        "dispute", "arbitration", "mediation", "governing law", "jurisdiction",
    ],
    "warranties": [
        "warrant", "represent", "guarantee", "assur",
    ],
    "auto_renewal": [
        "auto-renew", "automatic renewal", "renew automatically", "evergreen",
    ],
    "penalty": [
        "penalty", "penalti", "forfeit", "liquidated damages", "fine",
    ],
    "general": [],  # fallback
}


def _label_clause(text: str) -> str:
    """Return the best matching label for a clause."""
    text_lower = text.lower()
    best_label = "general"
    best_count = 0
    for label, keywords in CLAUSE_LABELS.items():
        if label == "general":
            continue
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_label = label
    return best_label


def segment_clauses(text: str) -> List[Dict]:
    """
    Split a legal document text into labeled clauses.
    Strategy: split on numbered headings, ALL-CAPS headings, or blank-line blocks.
    """
    # Pattern: numbered clause like "1.", "1.1", "Section 1", "CLAUSE 1"
    split_pattern = re.compile(
        r"(?m)(?=(?:^|\n)(?:\d+[\.\)]\s|\bSection\s+\d+|\bClause\s+\d+|\bARTICLE\s+[IVXLCDM\d]+))",
        re.IGNORECASE,
    )
    raw_parts = split_pattern.split(text)

    # If we got very few splits, fall back to paragraph-based segmentation
    if len(raw_parts) < 3:
        raw_parts = re.split(r"\n{2,}", text)

    clauses = []
    clause_id = 1
    for part in raw_parts:
        part = part.strip()
        if not part or len(part) < 30:
            continue
        title_match = re.match(r"^([^\n]{0,120})\n", part)
        title = title_match.group(1).strip() if title_match else f"Clause {clause_id}"
        label = _label_clause(part)
        clauses.append(
            {
                "id": clause_id,
                "title": title,
                "text": part,
                "label": label,
            }
        )
        clause_id += 1

    return clauses
