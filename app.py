"""
AI-Powered Legal Risk Analyzer for Contracts and Documents
----------------------------------------------------------
Flask application supporting:
  - Multi-format input: Image (JPG/PNG/…), PDF, DOCX, TXT, URL
  - OCR text extraction from images (OpenAI Vision → pytesseract fallback)
  - URL scraping with SSRF protection
  - Plain-language summary
  - Risk detection & classification (Safe / Moderate / High)
  - Rule / law violation detection with region support
  - Clause simplification (legal → plain English)
  - Annotated image output (PIL) and annotated PDF output (PyMuPDF)
  - Context-aware chatbot (document mode + general legal mode)
  - Voice output (browser Web Speech API + server-side gTTS fallback)
  - In-memory session management with auto-cleanup
"""

import base64
import io
import ipaddress
import os
import re
import socket
import time
import uuid
import hashlib
import json
import math
from collections import Counter
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Document parsers
import PyPDF2
from docx import Document as DocxDocument

# Image processing
try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# OCR
try:
    import pytesseract as _pytesseract_module

    def _check_tesseract() -> bool:
        try:
            _pytesseract_module.get_tesseract_version()
            return True
        except Exception:
            return False

    import pytesseract
    _TESSERACT_AVAILABLE = _check_tesseract()
except ImportError:
    _TESSERACT_AVAILABLE = False

# PDF annotation
try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

# URL scraping
try:
    import requests as http_requests
    from bs4 import BeautifulSoup
    _SCRAPING_AVAILABLE = True
except ImportError:
    _SCRAPING_AVAILABLE = False

# Optional OpenAI
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# Optional gTTS
try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False

load_dotenv()

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp"}
DOC_EXTENSIONS   = {"pdf", "txt", "docx"}
ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
SESSION_TTL = 3600  # 1 hour

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
_secret_key = os.environ.get("SECRET_KEY", "")
if not _secret_key:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production. "
            "Add it to your .env file."
        )
    _secret_key = "change-me-in-development"
app.secret_key = _secret_key
CORS(app)

# ---------------------------------------------------------------------------
# OpenAI client (optional)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_openai_client = None
if _OPENAI_AVAILABLE and OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# In-memory session store  { session_id -> {text, analysis, annotated_bytes,
#                                           content_type, ext, created_at} }
# ---------------------------------------------------------------------------
_sessions: dict = {}


def _cleanup_sessions() -> None:
    """Remove sessions older than SESSION_TTL."""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", 0) > SESSION_TTL]
    for sid in expired:
        _sessions.pop(sid, None)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _file_ext(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(filepath: str, filename: str) -> str:
    """Extract plain text from PDF, DOCX, TXT, or image files."""
    ext = _file_ext(filename)
    if ext in IMAGE_EXTENSIONS:
        return _extract_text_from_image(filepath)
    if ext == "pdf":
        text_parts = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    if ext == "docx":
        doc = DocxDocument(filepath)
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    # txt
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_text_from_image(filepath: str) -> str:
    """Extract text from an image using OpenAI Vision or pytesseract."""
    # Try OpenAI Vision (gpt-4o) first
    if _openai_client:
        try:
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = filepath.rsplit(".", 1)[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            response = _openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract ALL text from this legal document image exactly as written."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }],
                max_tokens=3000,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass  # fall through to tesseract

    # Try pytesseract
    if _TESSERACT_AVAILABLE and _PIL_AVAILABLE:
        try:
            img = Image.open(filepath)
            return pytesseract.image_to_string(img)
        except Exception:
            pass

    return ""


def _get_image_word_positions(filepath: str) -> list:
    """Return list of {text, x, y, w, h} dicts for each word in the image."""
    if not (_TESSERACT_AVAILABLE and _PIL_AVAILABLE):
        return []
    try:
        img = Image.open(filepath)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        results = []
        for i, word in enumerate(data["text"]):
            if word.strip() and int(data["conf"][i]) > 30:
                results.append({
                    "text": word,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                })
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# URL extraction (with SSRF protection)
# ---------------------------------------------------------------------------

def _is_safe_url(url: str) -> bool:
    """Return True only if the URL is safe to fetch (public HTTP/HTTPS, non-private IP).

    Blocks:
    - Non-HTTP(S) schemes
    - IP literals in private/loopback/link-local/reserved ranges
    - 'localhost' and loopback hostname aliases
    - Domains whose DNS resolves to private IPs
    - Domains when DNS resolution is unavailable (conservative rejection)
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        # If the hostname is a numeric IP literal, validate it directly
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
            return True  # valid public IP literal — no DNS needed
        except ValueError:
            pass  # not an IP literal — continue with domain-name checks

        # Block explicit loopback/localhost domain names
        if hostname.lower() in ("localhost", "ip6-localhost", "ip6-loopback"):
            return False

        # Resolve the hostname; reject conservatively if DNS is unavailable
        try:
            ip_str = socket.gethostbyname(hostname)
            resolved = ipaddress.ip_address(ip_str)
            if resolved.is_private or resolved.is_loopback or resolved.is_link_local or resolved.is_reserved:
                return False
        except OSError:
            # DNS unavailable — reject to be conservative
            return False

        return True
    except Exception:
        return False


def extract_text_from_url(url: str) -> str:
    """Fetch and extract visible text from a URL."""
    if not _SCRAPING_AVAILABLE:
        return ""
    if not _is_safe_url(url):
        raise ValueError("URL not allowed (must be a public http/https address).")
    resp = http_requests.get(
        url,
        timeout=10,
        stream=True,
        allow_redirects=False,          # prevent redirect-based SSRF
        headers={"User-Agent": "LegalDocAnalyzer/1.0"},
    )
    # Follow only safe redirects (re-validate each hop), limit to 5 hops
    MAX_REDIRECTS = 5
    redirect_count = 0
    while resp.is_redirect:
        if redirect_count >= MAX_REDIRECTS:
            raise ValueError("Too many redirects (max 5).")
        location = resp.headers.get("Location", "")
        if not _is_safe_url(location):
            raise ValueError("Redirect to a disallowed address blocked.")
        resp = http_requests.get(
            location,
            timeout=10,
            stream=True,
            allow_redirects=False,
            headers={"User-Agent": "LegalDocAnalyzer/1.0"},
        )
        redirect_count += 1
    resp.raise_for_status()
    # Limit download size to 2 MB; close connection on overflow
    content = b""
    MAX_BYTES = 2 * 1024 * 1024
    for chunk in resp.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_BYTES:
            resp.close()
            raise ValueError("URL content too large (max 2 MB).")
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


# ---------------------------------------------------------------------------
# AI Analysis helpers
# ---------------------------------------------------------------------------

def _call_openai(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Call OpenAI chat completion and return the response text."""
    if _openai_client is None:
        return ""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = _openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _parse_json_response(raw: str) -> dict | None:
    """Extract and parse the first JSON object from a string."""
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def generate_summary(text: str) -> str:
    """Generate a plain-language summary of the document."""
    if _openai_client:
        return _call_openai(
            prompt=(
                "Summarize the following legal document in plain, simple language "
                "anyone can understand. Highlight the main purpose, key obligations, "
                "important dates, and any significant clauses:\n\n" + text[:4000]
            ),
            system="You are a helpful legal assistant that explains legal documents in simple English.",
            max_tokens=600,
        )
    sentences = re.split(r"(?<=[.!?])\s+", text)
    meaningful = [s.strip() for s in sentences if len(s.split()) > 6][:8]
    return " ".join(meaningful) if meaningful else text[:500]


def detect_risks(text: str) -> dict:
    """Detect legal risks; return overall_risk_level, risk_score, risks[]."""
    if _openai_client:
        raw = _call_openai(
            prompt=(
                "Analyze the following legal document for potential risks. "
                "Return a JSON object with:\n"
                "  - overall_risk_level: 'Low', 'Medium', or 'High'\n"
                "  - risk_score: integer 0-100\n"
                "  - risks: list of objects with 'category', 'description', 'severity' ('Low'/'Medium'/'High'), "
                "and 'keyword' (the exact word/phrase from the document that triggered this risk)\n\n"
                "Document:\n" + text[:4000]
            ),
            system="You are a legal risk analyst. Always respond with valid JSON only.",
            max_tokens=900,
        )
        result = _parse_json_response(raw)
        if result:
            return result
    return _heuristic_risk(text)


def _heuristic_risk(text: str) -> dict:
    """Keyword-based risk heuristic when OpenAI is unavailable."""
    lower = text.lower()
    risks = []
    high_keywords = [
        ("indemnification", "Indemnification clause may expose you to significant financial liability."),
        ("unlimited liability", "Unlimited liability – your financial exposure is uncapped."),
        ("arbitration", "Mandatory arbitration limits your right to sue in court."),
        ("non-compete", "Non-compete clause restricts future employment or business."),
        ("automatic renewal", "Auto-renewal may lock you into continued obligations."),
        ("penalty", "Penalty clauses may impose heavy financial sanctions."),
        ("liquidated damages", "Pre-set damages clause that may be unfavorable."),
        ("forfeiture", "Forfeiture clause could result in loss of deposit or rights."),
        ("unilateral", "Unilateral changes can be made without your consent."),
    ]
    medium_keywords = [
        ("termination for convenience", "Either party can end the agreement without cause."),
        ("confidentiality", "Strict confidentiality obligations may limit information sharing."),
        ("intellectual property", "IP assignment may transfer ownership of your work."),
        ("governing law", "Jurisdiction may be inconvenient or unfamiliar to you."),
        ("force majeure", "Force majeure defines events that excuse performance."),
        ("warranty disclaimer", "Warranties disclaimed – you may have limited recourse."),
        ("exclusion of liability", "Liability exclusion may leave you without remedy."),
        ("security deposit", "Conditions on returning security deposit may be one-sided."),
    ]
    low_keywords = [
        ("notice", "Notice requirements must be followed precisely."),
        ("assignment", "Assignment restrictions may limit transfer of rights."),
        ("amendment", "Amendment clauses define how changes can be made."),
        ("waiver", "Waiver clauses may affect your ability to enforce rights."),
    ]
    for kw, desc in high_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "High", "keyword": kw})
    for kw, desc in medium_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "Medium", "keyword": kw})
    for kw, desc in low_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "Low", "keyword": kw})

    high_count   = sum(1 for r in risks if r["severity"] == "High")
    medium_count = sum(1 for r in risks if r["severity"] == "Medium")
    score = min(100, high_count * 20 + medium_count * 10 + len(risks) * 3)
    level = "High" if score >= 60 else "Medium" if score >= 30 else "Low"

    return {
        "overall_risk_level": level,
        "risk_score": score,
        "risks": risks or [{"category": "General", "description": "No specific high-risk clauses detected. Review manually.", "severity": "Low", "keyword": ""}],
    }


def generate_rule_violations(text: str, region: str = "India") -> dict:
    """Detect rule/law violations; return violations[], compliance_score."""
    if _openai_client:
        raw = _call_openai(
            prompt=(
                f"Analyze this legal document for violations of rules, laws, or regulations specific to {region}. "
                "Return a JSON object with:\n"
                "  - violations: list of objects with:\n"
                "      'rule': name of the law/rule violated,\n"
                "      'clause': exact short quote from the document (max 20 words),\n"
                "      'issue': why it is problematic,\n"
                "      'suggestion': what could be changed (as a suggestion, NOT a legal order)\n"
                "  - compliance_score: integer 0-100 (100 = fully compliant)\n\n"
                "Document:\n" + text[:4000]
            ),
            system=(
                f"You are a legal compliance expert specializing in {region} law. "
                "Always respond with valid JSON only. Provide suggestions, not legal advice."
            ),
            max_tokens=1000,
        )
        result = _parse_json_response(raw)
        if result:
            return result
    return _heuristic_violations(text, region)


def _heuristic_violations(text: str, region: str) -> dict:
    """Heuristic violation detection for common contract issues."""
    lower = text.lower()
    violations = []

    checks = [
        (
            "security deposit",
            "Rent Control Act / Consumer Protection",
            "Security deposit terms may exceed legal limits.",
            "Consider specifying that security deposit will not exceed the amount permitted under local rent laws.",
        ),
        (
            "notice period",
            "Contract Act",
            "Notice period clause may be unreasonably short or absent.",
            "Consider adding a minimum 30-day written notice period for termination.",
        ),
        (
            "unilateral",
            "Contract Act – Mutuality of Obligation",
            "Unilateral modifications give only one party the power to change terms.",
            "Consider requiring mutual written consent for any modifications.",
        ),
        (
            "no refund",
            "Consumer Protection Act",
            "'No refund' clauses may be unenforceable under consumer protection laws.",
            "Consider specifying fair refund conditions instead of a blanket no-refund policy.",
        ),
        (
            "arbitration",
            "Arbitration & Conciliation Act",
            "Mandatory arbitration without mutual agreement may limit legal recourse.",
            "Consider allowing choice between arbitration and regular court proceedings.",
        ),
        (
            "unlimited liability",
            "Indian Contract Act – Reasonableness",
            "Unlimited liability clauses are rarely enforceable and may be unfair.",
            "Consider capping liability to the contract value or insurance amount.",
        ),
        (
            "automatic renewal",
            "Consumer Protection Act",
            "Auto-renewal without explicit consent may be considered an unfair trade practice.",
            "Consider requiring explicit opt-in renewal at least 30 days before expiry.",
        ),
        (
            "non-compete",
            "Indian Contract Act Section 27",
            "Overly broad non-compete clauses may be void under Section 27 of the Indian Contract Act.",
            "Consider limiting non-compete to a reasonable time period and geographic scope.",
        ),
    ]

    for kw, rule, issue, suggestion in checks:
        if kw in lower:
            # Find a short snippet containing the keyword
            idx = lower.index(kw)
            snippet_start = max(0, idx - 30)
            snippet_end   = min(len(text), idx + len(kw) + 50)
            clause = "…" + text[snippet_start:snippet_end].strip() + "…"
            violations.append({
                "rule": rule,
                "clause": clause,
                "issue": issue,
                "suggestion": suggestion,
            })

    compliance_score = max(0, 100 - len(violations) * 12)
    return {"violations": violations, "compliance_score": compliance_score}


def simplify_clauses(text: str) -> list:
    """Return a list of {original, simplified} pairs for complex legal clauses."""
    if _openai_client:
        raw = _call_openai(
            prompt=(
                "Identify up to 6 complex legal clauses in this document and rewrite them in "
                "simple, everyday English. Return a JSON array of objects with:\n"
                "  - original: the original legal text (max 30 words)\n"
                "  - simplified: the plain-English version\n\n"
                "Document:\n" + text[:4000]
            ),
            system="You are a legal plain-language expert. Always respond with a valid JSON array only.",
            max_tokens=700,
        )
        # Try to parse as array
        arr_match = re.search(r"\[[\s\S]*\]", raw)
        if arr_match:
            try:
                return json.loads(arr_match.group())
            except json.JSONDecodeError:
                pass
    return _heuristic_simplify(text)


def _heuristic_simplify(text: str) -> list:
    """Provide simplified explanations for common legal phrases found in text."""
    replacements = [
        ("hereinafter referred to as",   "from now on called"),
        ("notwithstanding anything to the contrary", "even if other parts of this contract say otherwise"),
        ("in witness whereof",            "to show agreement"),
        ("null and void",                 "invalid and has no legal effect"),
        ("indemnify and hold harmless",   "protect and not hold responsible for losses"),
        ("at the sole discretion of",     "decided entirely by"),
        ("force majeure",                 "unexpected events outside anyone's control (like floods or strikes)"),
        ("liquidated damages",            "a pre-agreed amount of money paid if the contract is broken"),
        ("time is of the essence",        "deadlines in this contract must be strictly met"),
        ("without prejudice",             "this statement cannot be used as evidence in court later"),
    ]
    lower = text.lower()
    results = []
    for phrase, simple in replacements:
        if phrase in lower:
            results.append({"original": phrase, "simplified": simple})
    return results[:6]


def check_originality(text: str) -> dict:
    """Check document originality / plagiarism indicators."""
    doc_hash = hashlib.sha256(text.encode()).hexdigest()
    if _openai_client:
        raw = _call_openai(
            prompt=(
                "Analyze the following legal document text for signs of plagiarism or lack of originality. "
                "Return a JSON object with:\n"
                "  - originality_score: integer 0-100 (100 = fully original)\n"
                "  - verdict: 'Original', 'Likely Original', 'Possibly Copied', or 'Likely Plagiarized'\n"
                "  - findings: list of strings describing observations\n\n"
                "Document:\n" + text[:3000]
            ),
            system="You are a plagiarism detection expert. Always respond with valid JSON only.",
            max_tokens=500,
        )
        result = _parse_json_response(raw)
        if result:
            result["document_fingerprint"] = doc_hash[:16]
            return result
    return _heuristic_originality(text, doc_hash)


def _heuristic_originality(text: str, doc_hash: str) -> dict:
    words = re.findall(r"\b[a-z]+\b", text.lower())
    total_words = len(words)
    if total_words == 0:
        return {"originality_score": 0, "verdict": "Possibly Copied",
                "findings": ["No readable text found."], "document_fingerprint": doc_hash[:16]}

    unique_words    = len(set(words))
    vocab_richness  = round(unique_words / total_words * 100, 1)
    boilerplate_phrases = [
        "hereinafter referred to as", "in witness whereof",
        "notwithstanding anything to the contrary", "terms and conditions",
        "without limitation", "shall not be liable", "governing law",
        "entire agreement", "force majeure", "intellectual property rights",
    ]
    boilerplate_count = sum(1 for p in boilerplate_phrases if p in text.lower())
    boilerplate_ratio = boilerplate_count / len(boilerplate_phrases)
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    bigram_counts = Counter(bigrams)
    repeated_bigrams = sum(1 for c in bigram_counts.values() if c > 3)
    bigram_repetition_ratio = repeated_bigrams / max(len(bigram_counts), 1)

    score = int(50 + (vocab_richness - 50) * 0.4 - boilerplate_ratio * 25 - bigram_repetition_ratio * 15)
    score = max(0, min(100, score))
    if score >= 75:   verdict = "Original"
    elif score >= 55: verdict = "Likely Original"
    elif score >= 35: verdict = "Possibly Copied"
    else:             verdict = "Likely Plagiarized"

    findings = [
        f"Vocabulary richness: {vocab_richness}% unique words out of {total_words} total.",
        f"Boilerplate legal phrases detected: {boilerplate_count}/{len(boilerplate_phrases)}.",
        f"Repeated phrase patterns: {repeated_bigrams}.",
    ]
    if boilerplate_count >= 5:
        findings.append("High use of standard legal boilerplate language.")
    if vocab_richness > 60:
        findings.append("Strong vocabulary variety suggests original authorship.")

    return {"originality_score": score, "verdict": verdict,
            "findings": findings, "document_fingerprint": doc_hash[:16]}


# ---------------------------------------------------------------------------
# Risk keyword helpers (for annotation)
# ---------------------------------------------------------------------------

def _get_risk_keywords(risks: dict) -> list:
    """Extract all keyword strings from a risk analysis result."""
    keywords = []
    for r in risks.get("risks", []):
        kw = r.get("keyword", "")
        if kw:
            keywords.append(kw.lower())
        # Also add category words
        cat = r.get("category", "").lower()
        if cat and cat != "general":
            keywords.append(cat)
    return list(set(keywords))


# ---------------------------------------------------------------------------
# Annotated output generation
# ---------------------------------------------------------------------------

def create_annotated_image(filepath: str, risks: dict, violations: dict) -> bytes | None:
    """Return PNG bytes of the image annotated with risk highlights and a summary panel."""
    if not _PIL_AVAILABLE:
        return None
    try:
        img = Image.open(filepath).convert("RGB")
        draw_orig = ImageDraw.Draw(img, "RGBA")

        risk_keywords = _get_risk_keywords(risks)
        word_positions = _get_image_word_positions(filepath)

        # Highlight matching words on the original image
        COLORS = {"High": (220, 38, 38, 120), "Medium": (217, 119, 6, 110), "Low": (22, 163, 74, 100)}
        severity_map = {r.get("keyword", "").lower(): r.get("severity", "Low") for r in risks.get("risks", [])}
        if word_positions:
            for wp in word_positions:
                wtext = wp["text"].lower().rstrip(".,;:")
                for kw in risk_keywords:
                    if kw and (wtext == kw or kw in wtext):
                        sev = severity_map.get(kw, "Medium")
                        color = COLORS.get(sev, COLORS["Medium"])
                        x, y, w, h = wp["x"], wp["y"], wp["w"], wp["h"]
                        # Clamp all coordinates to image boundaries
                        x1 = max(0, x - 2)
                        y1 = max(0, y - 2)
                        x2 = min(img.width,  x + w + 2)
                        y2 = min(img.height, y + h + 2)
                        draw_orig.rectangle([x1, y1, x2, y2], fill=color)
                        break

        # Build annotation panel
        level        = risks.get("overall_risk_level", "Low")
        score        = risks.get("risk_score", 0)
        violations_n = len(violations.get("violations", []))
        panel_color  = (220, 38, 38) if level == "High" else (217, 119, 6) if level == "Medium" else (22, 163, 74)
        PANEL_H      = 120
        panel        = Image.new("RGB", (img.width, PANEL_H), panel_color)
        draw_panel   = ImageDraw.Draw(panel)

        try:
            font_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except Exception:
            font_big = font_small = ImageFont.load_default()

        draw_panel.text((16, 12), f"⚠ Risk Level: {level}  |  Score: {score}/100  |  Violations: {violations_n}", fill=(255, 255, 255), font=font_big)
        draw_panel.text((16, 48), "Highlighted sections indicate potential risks. Please review before signing.", fill=(255, 240, 200), font=font_small)
        draw_panel.text((16, 76), "AI-assisted insights only — not legal advice. Consult a qualified lawyer.", fill=(255, 240, 200), font=font_small)

        combined = Image.new("RGB", (img.width, img.height + PANEL_H), (255, 255, 255))
        combined.paste(img, (0, 0))
        combined.paste(panel, (0, img.height))

        out = io.BytesIO()
        combined.save(out, format="PNG")
        out.seek(0)
        return out.read()
    except Exception:
        return None


def create_annotated_pdf(filepath: str, risks: dict, violations: dict) -> bytes | None:
    """Return annotated PDF bytes with highlighted risk keywords and a summary page."""
    if not _PYMUPDF_AVAILABLE:
        return None
    try:
        doc = fitz.open(filepath)
        risk_keywords = _get_risk_keywords(risks)
        severity_map  = {r.get("keyword", "").lower(): r.get("severity", "Low") for r in risks.get("risks", [])}
        COLORS = {
            "High":   (1.0, 0.2, 0.2),
            "Medium": (1.0, 0.75, 0.0),
            "Low":    (0.6, 1.0, 0.6),
        }

        for page in doc:
            for kw in risk_keywords:
                if not kw:
                    continue
                instances = page.search_for(kw)
                sev   = severity_map.get(kw, "Medium")
                color = COLORS.get(sev, COLORS["Medium"])
                for rect in instances:
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.set_info(content=f"Risk: {sev} — {kw}")
                    annot.update()

        # Append a summary page
        level        = risks.get("overall_risk_level", "Low")
        score        = risks.get("risk_score", 0)
        violations_l = violations.get("violations", [])
        risks_l      = risks.get("risks", [])

        sum_page = doc.new_page(width=595, height=842)
        y = 50
        sum_page.insert_text((50, y), "Legal Risk Analysis Report", fontsize=20, fontname="helv", color=(0.1, 0.1, 0.6))
        y += 40
        sum_page.insert_text((50, y), f"Overall Risk: {level}  |  Score: {score}/100", fontsize=14, fontname="helv")
        y += 30
        sum_page.insert_text((50, y), f"Violations Found: {len(violations_l)}", fontsize=12, fontname="helv")
        y += 30
        sum_page.insert_text((50, y), "Risk Items:", fontsize=13, fontname="helv", color=(0.6, 0.0, 0.0))
        y += 20
        for r in risks_l[:10]:
            line = f"  [{r.get('severity','?')}] {r.get('category','?')}: {r.get('description','')}"
            sum_page.insert_text((50, y), line[:100], fontsize=10, fontname="helv")
            y += 18
            if y > 780:
                break
        if violations_l:
            y += 10
            sum_page.insert_text((50, y), "Rule Violations:", fontsize=13, fontname="helv", color=(0.6, 0.0, 0.0))
            y += 20
            for v in violations_l[:6]:
                sum_page.insert_text((50, y), f"  {v.get('rule','?')}", fontsize=10, fontname="helv")
                y += 16
                suggestion = v.get("suggestion", "")
                if suggestion:
                    sum_page.insert_text((60, y), f"  Suggestion: {suggestion[:90]}", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
                    y += 16
                if y > 780:
                    break
        y += 20
        sum_page.insert_text((50, y), "AI-assisted insights only — not legal advice. Consult a qualified lawyer.", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))

        out = io.BytesIO()
        doc.save(out)
        out.seek(0)
        return out.read()
    except Exception:
        return None


def create_annotated_url_report(text: str, url: str, risks: dict, violations: dict, summary: str) -> bytes | None:
    """Generate a PDF analysis report for URL input."""
    if not _PYMUPDF_AVAILABLE:
        return None
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        y = 40

        def _write(txt, fs=11, color=(0, 0, 0), indent=50):
            nonlocal y
            # Wrap long text
            words = txt.split()
            line, lines = "", []
            for w in words:
                test = (line + " " + w).strip()
                if len(test) > 85:
                    lines.append(line)
                    line = w
                else:
                    line = test
            if line:
                lines.append(line)
            for l in lines:
                if y > 800:
                    return
                page.insert_text((indent, y), l, fontsize=fs, fontname="helv", color=color)
                y += fs + 5

        _write("Legal Risk Analysis Report — URL Input", fs=18, color=(0.1, 0.1, 0.6))
        y += 6
        _write(f"Source: {url[:80]}", fs=9, color=(0.4, 0.4, 0.4))
        y += 14

        level = risks.get("overall_risk_level", "Low")
        score = risks.get("risk_score", 0)
        _write(f"Overall Risk: {level}  |  Score: {score}/100", fs=13)
        y += 10

        _write("Summary:", fs=13, color=(0.1, 0.1, 0.6))
        _write(summary[:600], fs=10)
        y += 10

        _write("Risk Items:", fs=13, color=(0.6, 0.0, 0.0))
        for r in risks.get("risks", [])[:8]:
            _write(f"  [{r.get('severity','?')}] {r.get('category','?')}: {r.get('description','')}", fs=10)

        violations_l = violations.get("violations", [])
        if violations_l:
            y += 10
            _write("Rule Violations:", fs=13, color=(0.6, 0.0, 0.0))
            for v in violations_l[:6]:
                _write(f"  {v.get('rule','?')}", fs=10)
                if v.get("suggestion"):
                    _write(f"    Suggestion: {v['suggestion'][:90]}", fs=9, color=(0.3, 0.3, 0.3))

        y += 14
        _write("AI-assisted insights only — not legal advice. Consult a qualified lawyer.", fs=9, color=(0.5, 0.5, 0.5))

        out = io.BytesIO()
        doc.save(out)
        out.seek(0)
        return out.read()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------

def _chatbot_response(message: str, doc_context: str, chat_history: list, region: str = "India") -> str:
    """Generate a chatbot reply using OpenAI or a heuristic fallback."""
    if _openai_client:
        system = (
            f"You are a helpful legal assistant specializing in {region} law. "
            "You provide clear, simple explanations of legal concepts. "
            "You always remind users that your responses are for information purposes only "
            "and are not legal advice. Never tell users what they MUST do—only suggest options."
        )
        if doc_context:
            system += (
                "\n\nThe user has uploaded a legal document. "
                "Answer questions specifically about this document when asked. "
                "Here is the document content (first 3000 characters):\n\n"
                + doc_context[:3000]
            )
        messages = [{"role": "system", "content": system}]
        # Add last 6 messages of history
        for h in chat_history[-6:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})
        try:
            response = _openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=600,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "Sorry, I couldn't process your question right now. Please try again."

    return _heuristic_chat_response(message, doc_context)


def _heuristic_chat_response(message: str, doc_context: str) -> str:
    """Rule-based fallback chatbot responses."""
    lower = message.lower()
    if any(w in lower for w in ["hello", "hi", "hey", "help"]):
        if doc_context:
            return "Hello! I've reviewed your uploaded document. Ask me anything about it — like 'What are the risks?' or 'What does clause X mean?'"
        return "Hello! I'm your legal assistant. You can upload a document and I'll answer questions about it, or ask me general legal questions."

    if doc_context:
        if any(w in lower for w in ["risk", "dangerous", "unsafe", "problem"]):
            return "Based on your document, I detected potential risks such as unfair clauses or one-sided terms. Please check the Risk Analysis section above for details."
        if any(w in lower for w in ["summary", "about", "what is", "explain"]):
            return "Your document appears to be a legal agreement. Please see the Plain-Language Summary section above for a full breakdown."
        if any(w in lower for w in ["sign", "safe", "should i"]):
            return "I can only provide informational guidance, not legal advice. Please review the highlighted risks and consult a lawyer before signing anything important."
        if any(w in lower for w in ["violation", "illegal", "law", "rule"]):
            return "Check the Rule Violations section above. It lists specific clauses that may conflict with applicable laws, along with suggestions for improvement."
        return "I'm here to help you understand your document. Try asking: 'What are the main risks?' or 'Is this agreement safe?'"

    # General mode
    if any(w in lower for w in ["rent", "lease", "tenant", "landlord"]):
        return ("Rental agreements typically cover rent amount, duration, notice period, security deposit, and maintenance responsibilities. "
                "Key risks to watch: auto-renewal clauses, one-sided termination, and excessive penalties. "
                "This is general information only — not legal advice.")
    if any(w in lower for w in ["contract", "agreement", "sign"]):
        return ("Before signing any contract, check: who the parties are, what obligations each party has, "
                "termination conditions, penalties, and governing law. "
                "This is general information only — not legal advice.")
    if any(w in lower for w in ["non-compete", "non compete"]):
        return ("Non-compete clauses restrict your ability to work in a similar field after leaving a job. "
                "In India, overly broad non-competes may be unenforceable under Section 27 of the Indian Contract Act. "
                "This is general information only — not legal advice.")
    if any(w in lower for w in ["arbitration", "court", "dispute"]):
        return ("Arbitration is an alternative to court where a neutral arbitrator decides disputes. "
                "It is usually faster and cheaper but limits your appeal options. "
                "This is general information only — not legal advice.")
    return ("I'm a legal document assistant. Upload a document to get specific insights, "
            "or ask me general questions about contracts, agreements, or legal terms. "
            "Remember: I provide information only, not legal advice.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Analyze a document (file upload or URL) and return full analysis."""
    _cleanup_sessions()

    region = request.form.get("region") or (
        (request.get_json(silent=True) or {}).get("region")
    ) or "India"
    region = region.strip()[:64]

    input_url      = None
    filepath       = None
    filename       = None
    original_bytes = None
    file_ext       = None

    # ── URL input ──
    url_input = request.form.get("url", "").strip()
    if url_input:
        if not _SCRAPING_AVAILABLE:
            return jsonify({"error": "URL analysis is not available on this server."}), 503
        try:
            text = extract_text_from_url(url_input)
        except ValueError as ve:
            # ValueError messages are controlled by our own code and safe to expose
            return jsonify({"error": ve.args[0] if ve.args else "Invalid URL."}), 400
        except Exception:
            return jsonify({"error": "Failed to fetch URL. Please check the link and try again."}), 422
        if not text.strip():
            return jsonify({"error": "Could not extract any text from the URL."}), 422
        input_url = url_input
        filename  = "url_document"
        file_ext  = "url"

    # ── File input ──
    elif "file" in request.files:
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No file selected."}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Unsupported file type. Upload PDF, DOCX, TXT, or an image."}), 400

        filename    = secure_filename(file.filename)
        file_ext    = _file_ext(filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        filepath    = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)

        if file_ext in IMAGE_EXTENSIONS:
            with open(filepath, "rb") as img_f:
                original_bytes = img_f.read()

        try:
            text = extract_text(filepath, filename)
        except Exception:
            return jsonify({"error": "Failed to read document. Please ensure the file is not corrupted."}), 422

    else:
        return jsonify({"error": "Please upload a file or provide a URL."}), 400

    if not text.strip():
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": (
            "Document is empty or unreadable. "
            "For images, ensure the text is legible. "
            "An OpenAI API key enables Vision-based OCR."
        )}), 422

    # ── Run analyses ──
    summary    = generate_summary(text)
    risks      = detect_risks(text)
    violations = generate_rule_violations(text, region)
    simplified = simplify_clauses(text)
    originality = check_originality(text)

    # ── Generate annotated output ──
    annotated_bytes   = None
    annotated_mime    = None
    annotated_ext_out = None

    if file_ext in IMAGE_EXTENSIONS and filepath and _PIL_AVAILABLE:
        annotated_bytes   = create_annotated_image(filepath, risks, violations)
        annotated_mime    = "image/png"
        annotated_ext_out = "png"
    elif file_ext == "pdf" and filepath and _PYMUPDF_AVAILABLE:
        annotated_bytes   = create_annotated_pdf(filepath, risks, violations)
        annotated_mime    = "application/pdf"
        annotated_ext_out = "pdf"
    elif file_ext == "url" and _PYMUPDF_AVAILABLE:
        annotated_bytes   = create_annotated_url_report(text, input_url, risks, violations, summary)
        annotated_mime    = "application/pdf"
        annotated_ext_out = "pdf"

    # ── Store session ──
    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "text":             text,
        "filename":         filename,
        "region":           region,
        "analysis":         {"summary": summary, "risks": risks, "violations": violations},
        "annotated_bytes":  annotated_bytes,
        "annotated_mime":   annotated_mime,
        "annotated_ext":    annotated_ext_out,
        "created_at":       time.time(),
    }

    # ── Cleanup uploaded file ──
    if filepath and os.path.exists(filepath):
        os.remove(filepath)

    return jsonify({
        "session_id":       session_id,
        "filename":         filename,
        "input_type":       file_ext,
        "word_count":       len(text.split()),
        "region":           region,
        "ai_powered":       _openai_client is not None,
        "summary":          summary,
        "risk_analysis":    risks,
        "violations":       violations,
        "simplified_clauses": simplified,
        "originality":      originality,
        "annotated_available": annotated_bytes is not None,
        "annotated_ext":    annotated_ext_out,
    })


@app.route("/api/download/<session_id>")
def download_annotated(session_id):
    """Download the annotated document for a given session."""
    # Validate session_id format (hex, case-insensitive)
    if not re.fullmatch(r"[0-9a-fA-F]{32}", session_id):
        return jsonify({"error": "Invalid session ID."}), 400
    session = _sessions.get(session_id.lower())
    if not session:
        return jsonify({"error": "Session not found or expired."}), 404
    data  = session.get("annotated_bytes")
    mime  = session.get("annotated_mime", "application/octet-stream")
    ext   = session.get("annotated_ext", "bin")
    fname = session.get("filename", "document")
    if not data:
        return jsonify({"error": "No annotated output available for this session."}), 404
    return send_file(
        io.BytesIO(data),
        mimetype=mime,
        as_attachment=True,
        download_name=f"annotated_{fname}.{ext}",
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    """Context-aware chatbot endpoint."""
    data = request.get_json(silent=True) or {}
    message     = (data.get("message") or "").strip()
    session_id  = (data.get("session_id") or "").strip()
    chat_history = data.get("chat_history") or []
    region      = (data.get("region") or "India").strip()[:64]

    if not message:
        return jsonify({"error": "No message provided."}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)."}), 400

    # Validate and normalise session_id (accept both upper and lower hex)
    doc_context = ""
    if session_id and re.fullmatch(r"[0-9a-fA-F]{32}", session_id):
        normalised_sid = session_id.lower()
        session = _sessions.get(normalised_sid)
        if session:
            doc_context = session.get("text", "")
            region      = session.get("region", region)

    # Sanitise chat_history: only keep role + content fields
    safe_history = [
        {"role": h["role"], "content": str(h["content"])[:1000]}
        for h in chat_history
        if isinstance(h, dict) and h.get("role") in ("user", "assistant")
    ][-10:]

    reply = _chatbot_response(message, doc_context, safe_history, region)
    return jsonify({"reply": reply})


@app.route("/api/voice", methods=["POST"])
def voice():
    """Convert text to speech using gTTS and return an MP3 audio stream."""
    if not _GTTS_AVAILABLE:
        return jsonify({"error": "gTTS not available on this server."}), 503

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    text = text[:2000]
    try:
        tts    = gTTS(text=text, lang="en", slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return send_file(mp3_fp, mimetype="audio/mpeg", as_attachment=False)
    except Exception:
        return jsonify({"error": "TTS generation failed. Please try again."}), 500


@app.route("/api/health")
def health():
    return jsonify({
        "status":            "ok",
        "openai_available":  _openai_client is not None,
        "gtts_available":    _GTTS_AVAILABLE,
        "pil_available":     _PIL_AVAILABLE,
        "pymupdf_available": _PYMUPDF_AVAILABLE,
        "tesseract_available": _TESSERACT_AVAILABLE,
        "scraping_available":  _SCRAPING_AVAILABLE,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
