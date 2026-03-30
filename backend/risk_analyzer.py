import re
from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# Risk keywords with weights
# ─────────────────────────────────────────────────────────────────────────────
RISK_RULES = [
    {
        "id": "unlimited_liability",
        "label": "Unlimited Liability",
        "patterns": [r"unlimited\s+liability", r"liability.{0,40}unlimited", r"no\s+cap\s+on\s+liability"],
        "severity": "high",
        "score": 2,
        "reason": "Unlimited liability exposes you to unbounded financial risk.",
        "suggestion": 'Cap liability to the total contract value, e.g., "Liability shall not exceed the total fees paid under this Agreement."',
    },
    {
        "id": "indemnity_broad",
        "label": "Broad Indemnity Clause",
        "patterns": [r"indemnif.{0,80}any\s+and\s+all", r"indemnif.{0,80}whatsoever", r"indemnif.{0,80}third.party"],
        "severity": "high",
        "score": 2,
        "reason": "Broad indemnity clauses may require you to cover all third-party claims without limit.",
        "suggestion": "Narrow indemnity to direct damages caused solely by your own negligence.",
    },
    {
        "id": "auto_renewal",
        "label": "Auto-Renewal Trap",
        "patterns": [r"auto.renew", r"automatic.{0,20}renewal", r"renew\s+automatically", r"evergreen"],
        "severity": "medium",
        "score": 1,
        "reason": "Auto-renewal clauses can lock you into renewed contracts without explicit consent.",
        "suggestion": "Add a notice period (e.g., 30 days) before renewal to allow opt-out.",
    },
    {
        "id": "penalty_heavy",
        "label": "Penalty-Heavy Terms",
        "patterns": [r"liquidated\s+damages", r"penalty.{0,30}clause", r"punitive.{0,20}damages", r"forfeit.{0,30}deposit"],
        "severity": "medium",
        "score": 1,
        "reason": "Heavy penalty terms may be disproportionate and unenforceable in some jurisdictions.",
        "suggestion": "Ensure penalties are reasonable and proportional to actual losses.",
    },
    {
        "id": "one_sided_termination",
        "label": "One-Sided Termination Rights",
        "patterns": [r"(?:company|employer|party\s+a).{0,60}terminat.{0,40}at\s+(?:its\s+)?(?:sole\s+)?discretion",
                     r"terminat.{0,40}without\s+cause.{0,40}at\s+any\s+time"],
        "severity": "medium",
        "score": 1,
        "reason": "Only one party has unrestricted termination rights, creating imbalance.",
        "suggestion": "Ensure termination rights are mutual or provide adequate notice periods.",
    },
    {
        "id": "vague_language",
        "label": "Vague or Ambiguous Language",
        "patterns": [r"as\s+deemed\s+appropriate", r"at\s+(?:our|their|its)\s+discretion\s+without",
                     r"such\s+other\s+(?:terms|conditions)\s+as\s+(?:we|they|it)\s+may"],
        "severity": "low",
        "score": 1,
        "reason": "Vague language gives one party unchecked discretion, which can be exploited.",
        "suggestion": "Replace discretionary language with specific, measurable criteria.",
    },
    {
        "id": "unilateral_modification",
        "label": "Unilateral Modification Rights",
        "patterns": [r"(?:may|reserves?\s+the\s+right\s+to)\s+(?:change|modify|amend)\s+(?:these\s+)?terms\s+at\s+any\s+time",
                     r"amend.{0,30}without\s+(?:prior\s+)?notice"],
        "severity": "high",
        "score": 2,
        "reason": "One party can change contract terms without your consent.",
        "suggestion": "Require mutual written consent for any material modifications.",
    },
    {
        "id": "ip_assignment",
        "label": "Broad IP Assignment",
        "patterns": [r"all\s+intellectual\s+property.{0,60}assign", r"work\s+for\s+hire",
                     r"assign.{0,40}all\s+rights.{0,40}title"],
        "severity": "medium",
        "score": 1,
        "reason": "Broad IP assignment may transfer all your creative work without compensation.",
        "suggestion": "Limit IP assignment to work created specifically under this contract.",
    },
]


def _check_missing_clauses(clauses: List[Dict]) -> List[Dict]:
    """Detect structurally missing important clauses."""
    missing = []
    labels = {c["label"] for c in clauses}

    if "termination" not in labels:
        missing.append({
            "id": "missing_termination",
            "label": "Missing Termination Clause",
            "severity": "high",
            "score": 2,
            "reason": "No termination clause found. Without it, the contract may be perpetual.",
            "suggestion": "Add a termination clause specifying conditions, notice period, and consequences.",
            "clause_id": None,
            "matched_text": None,
        })

    if "dispute_resolution" not in labels:
        missing.append({
            "id": "missing_dispute_resolution",
            "label": "Missing Dispute Resolution",
            "severity": "medium",
            "score": 1,
            "reason": "No dispute resolution mechanism specified.",
            "suggestion": "Include arbitration or mediation clause to avoid costly litigation.",
            "clause_id": None,
            "matched_text": None,
        })

    if "confidentiality" not in labels:
        missing.append({
            "id": "missing_confidentiality",
            "label": "Missing Confidentiality Clause",
            "severity": "low",
            "score": 1,
            "reason": "No confidentiality clause — sensitive information may not be protected.",
            "suggestion": "Add an NDA/confidentiality clause covering all proprietary information.",
            "clause_id": None,
            "matched_text": None,
        })

    return missing


def analyze_risks(clauses: List[Dict], doc_type: str = "contract") -> Dict:
    """
    Run all risk rules over every clause.
    Returns overall level, score breakdown, and per-clause findings.
    """
    all_findings: List[Dict] = []
    total_score = 0

    for clause in clauses:
        text = clause["text"]
        text_lower = text.lower()
        for rule in RISK_RULES:
            for pattern in rule["patterns"]:
                match = re.search(pattern, text_lower)
                if match:
                    snippet_start = max(0, match.start() - 40)
                    snippet_end = min(len(text), match.end() + 60)
                    all_findings.append({
                        "id": rule["id"],
                        "label": rule["label"],
                        "severity": rule["severity"],
                        "score": rule["score"],
                        "reason": rule["reason"],
                        "suggestion": rule["suggestion"],
                        "clause_id": clause["id"],
                        "clause_title": clause.get("title", ""),
                        "matched_text": text[snippet_start:snippet_end].strip(),
                    })
                    total_score += rule["score"]
                    break  # one match per rule per clause is enough

    # Structural checks
    missing = _check_missing_clauses(clauses)
    for m in missing:
        total_score += m["score"]
    all_findings.extend(missing)

    # Deduplicate by rule id
    seen_ids: set = set()
    unique_findings: List[Dict] = []
    for f in all_findings:
        key = (f["id"], f.get("clause_id"))
        if key not in seen_ids:
            seen_ids.add(key)
            unique_findings.append(f)

    # Determine overall level
    if total_score <= 1:
        level = "low"
    elif total_score <= 3:
        level = "medium"
    else:
        level = "high"

    high_count = sum(1 for f in unique_findings if f["severity"] == "high")
    medium_count = sum(1 for f in unique_findings if f["severity"] == "medium")
    low_count = sum(1 for f in unique_findings if f["severity"] == "low")

    return {
        "level": level,
        "score": total_score,
        "findings": unique_findings,
        "summary": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total": len(unique_findings),
        },
    }
