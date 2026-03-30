import re
from typing import Dict, List, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _first_match(patterns: List[str], text: str) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip() if m.lastindex else m.group(0).strip()
            # Clean stray punctuation
            value = re.sub(r"[,;\.]+$", "", value).strip()
            if len(value) > 2:
                return value
    return None


def extract_land_details(text: str) -> Dict[str, Optional[str]]:
    """Extract structured fields from a land / property document."""

    details: Dict[str, Optional[str]] = {}

    # Owner / Seller name
    details["owner_name"] = _first_match(
        [
            r"(?:owner|seller|vendor|grantor|purchaser|vendee)\s*[:\-]\s*([A-Z][a-zA-Z]{1,20}(?:\s+[A-Z][a-zA-Z]{1,20}){0,3})",
            r"(?:Sri|Smt|Mr|Mrs|Ms)\.?\s+([A-Z][a-zA-Z]{1,20}(?:\s+[A-Z][a-zA-Z]{1,20}){0,3})",
            r"I,\s+([A-Z][a-zA-Z]{1,20}(?:\s+[A-Z][a-zA-Z]{1,20}){0,3}),\s+(?:the\s+)?(?:owner|seller|vendor)",
        ],
        text,
    )

    # Survey number
    details["survey_number"] = _first_match(
        [
            r"(?:survey\s*(?:no|number|#))[:\.\s]+([A-Z0-9\/\-]+)",
            r"S\.?No\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)",
            r"Khasra\s*No\.?\s*[:\-]?\s*([A-Z0-9\/\-]+)",
        ],
        text,
    )

    # Plot number
    details["plot_number"] = _first_match(
        [
            r"(?:plot\s*(?:no|number|#))[:\.\s]+([A-Z0-9\/\-]+)",
            r"(?:flat|unit|door)\s*(?:no|number)\s*[:\-]?\s*([A-Z0-9\/\-]+)",
        ],
        text,
    )

    # Location / Address
    details["location"] = _first_match(
        [
            r"(?:located\s+(?:at|in)|situated\s+(?:at|in)|property\s+address)[:\.\s]+([^,\n]{5,80})",
            r"(?:village|district|mandal|taluk|tehsil)\s+of\s+([A-Za-z\s,]{3,60})",
            r"(?:at|in)\s+([A-Z][a-zA-Z\s,]{3,60}),\s+(?:State|District|Taluk|Mandal)",
        ],
        text,
    )

    # Land area
    details["area"] = _first_match(
        [
            r"(?:area|extent|total\s+area)\s*(?:of|is|:)?\s*([\d,\.]+\s*(?:sq\.?\s*(?:ft|m|yard|yd|meter)|acre|cent|gunta|hectare))",
            r"([\d,\.]+\s*(?:sq\.?\s*(?:ft|m|yard|yd)|acre|cent|gunta|hectare))\s*(?:of\s+land|plot|property)?",
        ],
        text,
    )

    # Registration number
    details["registration_number"] = _first_match(
        [
            r"(?:registration\s*(?:no|number|#)|doc(?:ument)?\s*(?:no|number))\s*[:\-]?\s*([A-Z0-9\/\-]+)",
            r"(?:registered\s+(?:under|as|vide))\s+(?:No\.?\s*)?([A-Z0-9\/\-]+)",
        ],
        text,
    )

    # Registration date
    details["registration_date"] = _first_match(
        [
            r"(?:registered\s+on|date\s+of\s+registration|executed\s+on)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            r"(?:on\s+this\s+)(\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+\s+\d{4})",
        ],
        text,
    )

    # Patta / Khata number
    details["patta_number"] = _first_match(
        [
            r"(?:patta|khata|khesra)\s*(?:no|number)\s*[:\-]?\s*([A-Z0-9\/\-]+)",
        ],
        text,
    )

    return details


# ─────────────────────────────────────────────────────────────────────────────
# Validation checks
# ─────────────────────────────────────────────────────────────────────────────

APPROVAL_KEYWORDS = [
    "municipality", "municipal corporation", "panchayat", "hmda",
    "dtcp", "cmda", "bda", "rera", "approved by", "layout approval",
    "building permission", "local authority", "town planning",
    "government approved", "govt. approved",
]

ENCUMBRANCE_KEYWORDS = [
    "encumbrance", "encumb", "ec ", "mortgage", "lien", "charge",
    "hypothecated", "free from encumbrance", "no encumbrance",
    "clear title", "free hold", "freehold",
]


def validate_land_document(text: str, details: Dict) -> Dict:
    """
    Run legal validation checks on a land document.
    Returns checks dict, findings list, risk level, and score.
    """
    text_lower = text.lower()

    checks = {
        "ownership_clarity": {
            "status": bool(details.get("owner_name")),
            "label": "Ownership Clarity",
            "description": "Seller / owner clearly identified",
        },
        "registration_present": {
            "status": bool(details.get("registration_number")),
            "label": "Registration Details",
            "description": "Registration number present",
        },
        "encumbrance_mentioned": {
            "status": any(kw in text_lower for kw in ENCUMBRANCE_KEYWORDS),
            "label": "Encumbrance Status",
            "description": "Encumbrance / mortgage information present",
        },
        "approval_authority": {
            "status": any(kw in text_lower for kw in APPROVAL_KEYWORDS),
            "label": "Government Approval",
            "description": "Approved by a local/government authority",
        },
        "survey_number_present": {
            "status": bool(details.get("survey_number")),
            "label": "Survey Number",
            "description": "Survey/plot number identified",
        },
        "area_mentioned": {
            "status": bool(details.get("area")),
            "label": "Land Area",
            "description": "Property area/extent mentioned",
        },
    }

    findings: List[Dict] = []
    score = 0

    if not checks["approval_authority"]["status"]:
        findings.append({
            "severity": "high",
            "label": "Missing Approval Authority",
            "reason": "No government or local authority approval found in the document. Land legality cannot be confirmed.",
            "suggestion": "Obtain RERA/HMDA/Municipality approval certificate and attach with the deed.",
        })
        score += 3

    if not checks["encumbrance_mentioned"]["status"]:
        findings.append({
            "severity": "medium",
            "label": "Encumbrance Not Mentioned",
            "reason": "No encumbrance or mortgage information found. The property may have hidden liabilities.",
            "suggestion": "Attach an Encumbrance Certificate (EC) for the last 15–30 years.",
        })
        score += 2

    if not checks["ownership_clarity"]["status"]:
        findings.append({
            "severity": "high",
            "label": "Ownership Not Clear",
            "reason": "Seller/owner name could not be extracted from the document.",
            "suggestion": "Ensure the document clearly identifies all owners and their share of ownership.",
        })
        score += 2

    if not checks["survey_number_present"]["status"]:
        findings.append({
            "severity": "medium",
            "label": "Survey Number Missing",
            "reason": "Survey/plot number not found — the land cannot be precisely identified.",
            "suggestion": "Include survey number, village, district and sub-registrar office details.",
        })
        score += 1

    if not checks["registration_present"]["status"]:
        findings.append({
            "severity": "medium",
            "label": "Registration Details Missing",
            "reason": "Registration number not found. Unregistered deeds may not be legally enforceable.",
            "suggestion": "Ensure the deed is registered with the Sub-Registrar's Office.",
        })
        score += 1

    # Overall verdict
    if score == 0:
        level = "low"
        verdict = "All major legal elements are present. Document appears complete."
    elif score <= 3:
        level = "medium"
        verdict = "Some legal elements are missing or unclear. Further verification is recommended."
    else:
        level = "high"
        verdict = "Critical legal information is missing. This document is INCOMPLETE — do not proceed without professional legal advice."

    return {
        "checks": checks,
        "findings": findings,
        "level": level,
        "score": score,
        "verdict": verdict,
    }
