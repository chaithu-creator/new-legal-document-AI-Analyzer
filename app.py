"""
Legal Document AI Analyzer
--------------------------
Flask application for uploading legal documents and running:
  - Plain-language summary
  - Risk detection
  - Originality / plagiarism check
  - Voice output (browser Web Speech API + server-side gTTS fallback)
"""

import io
import os
import re
import uuid
import hashlib
import json
import math
from collections import Counter

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Document parsers
import PyPDF2
from docx import Document as DocxDocument

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
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

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
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text(filepath: str, filename: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT files."""
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "pdf":
        text_parts = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    elif ext == "docx":
        doc = DocxDocument(filepath)
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    else:  # txt
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


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


def generate_summary(text: str) -> str:
    """Generate a plain-language summary of the document."""
    if _openai_client:
        snippet = text[:4000]
        return _call_openai(
            prompt=(
                "Please summarize the following legal document in plain, simple language "
                "that anyone can understand. Highlight the main purpose, key obligations, "
                "and important dates or deadlines:\n\n" + snippet
            ),
            system="You are a helpful legal assistant that explains legal documents in simple English.",
            max_tokens=600,
        )
    # Fallback: extract first meaningful sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    meaningful = [s.strip() for s in sentences if len(s.split()) > 6][:8]
    return " ".join(meaningful) if meaningful else text[:500]


def detect_risks(text: str) -> dict:
    """Detect legal risks in the document."""
    if _openai_client:
        snippet = text[:4000]
        raw = _call_openai(
            prompt=(
                "Analyze the following legal document for potential risks. "
                "Return a JSON object with:\n"
                "  - overall_risk_level: 'Low', 'Medium', or 'High'\n"
                "  - risk_score: integer 0-100\n"
                "  - risks: list of objects with 'category', 'description', and 'severity' ('Low'/'Medium'/'High')\n\n"
                "Document:\n" + snippet
            ),
            system="You are a legal risk analyst. Always respond with valid JSON only.",
            max_tokens=800,
        )
        # Extract JSON block if wrapped in markdown code fences
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    # Fallback heuristic analysis
    return _heuristic_risk(text)


def _heuristic_risk(text: str) -> dict:
    """Simple keyword-based risk heuristic when OpenAI is unavailable."""
    lower = text.lower()
    risks = []
    high_keywords = [
        ("indemnification", "Indemnification clauses may expose you to significant financial liability."),
        ("unlimited liability", "Unlimited liability clause found – your exposure is uncapped."),
        ("arbitration", "Mandatory arbitration limits your right to sue in court."),
        ("non-compete", "Non-compete clause restricts future employment or business activities."),
        ("automatic renewal", "Auto-renewal clause may lock you into continued obligations."),
        ("penalty", "Penalty clauses may impose financial sanctions."),
        ("liquidated damages", "Pre-set damages clause that may be unfavorable."),
    ]
    medium_keywords = [
        ("termination for convenience", "Either party can end the agreement without cause."),
        ("confidentiality", "Strict confidentiality obligations may limit information sharing."),
        ("intellectual property", "IP assignment clauses may transfer ownership of your work."),
        ("governing law", "The governing law/jurisdiction may be inconvenient or unfamiliar."),
        ("force majeure", "Force majeure clause defines uncontrollable events that excuse performance."),
        ("warranty disclaimer", "Warranties are disclaimed – you may have limited recourse."),
    ]
    low_keywords = [
        ("notice", "Notice requirements must be followed precisely."),
        ("assignment", "Assignment restrictions may limit transfer of rights."),
        ("amendment", "Amendment clauses define how changes can be made."),
    ]
    for kw, desc in high_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "High"})
    for kw, desc in medium_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "Medium"})
    for kw, desc in low_keywords:
        if kw in lower:
            risks.append({"category": kw.title(), "description": desc, "severity": "Low"})

    high_count = sum(1 for r in risks if r["severity"] == "High")
    medium_count = sum(1 for r in risks if r["severity"] == "Medium")
    score = min(100, high_count * 20 + medium_count * 10 + len(risks) * 3)
    if score >= 60:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    return {
        "overall_risk_level": level,
        "risk_score": score,
        "risks": risks if risks else [
            {
                "category": "General",
                "description": "No specific high-risk clauses detected. Review manually.",
                "severity": "Low",
            }
        ],
    }


def check_originality(text: str) -> dict:
    """Check document originality / plagiarism indicators."""
    doc_hash = hashlib.sha256(text.encode()).hexdigest()

    if _openai_client:
        snippet = text[:3000]
        raw = _call_openai(
            prompt=(
                "Analyze the following legal document text for signs of plagiarism or lack of originality. "
                "Return a JSON object with:\n"
                "  - originality_score: integer 0-100 (100 = fully original)\n"
                "  - verdict: 'Original', 'Likely Original', 'Possibly Copied', or 'Likely Plagiarized'\n"
                "  - findings: list of strings describing your observations\n\n"
                "Document:\n" + snippet
            ),
            system="You are a plagiarism detection expert. Always respond with valid JSON only.",
            max_tokens=500,
        )
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            try:
                result = json.loads(json_match.group())
                result["document_fingerprint"] = doc_hash[:16]
                return result
            except json.JSONDecodeError:
                pass

    # Fallback: statistical originality heuristic
    return _heuristic_originality(text, doc_hash)


def _heuristic_originality(text: str, doc_hash: str) -> dict:
    """Heuristic originality analysis based on text statistics."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    total_words = len(words)
    if total_words == 0:
        return {
            "originality_score": 0,
            "verdict": "Possibly Copied",
            "findings": ["Document appears to have no readable text."],
            "document_fingerprint": doc_hash[:16],
        }

    unique_words = len(set(words))
    vocab_richness = round(unique_words / total_words * 100, 1)

    # Common boilerplate legal phrases that lower originality
    boilerplate_phrases = [
        "hereinafter referred to as",
        "in witness whereof",
        "notwithstanding anything to the contrary",
        "terms and conditions",
        "without limitation",
        "shall not be liable",
        "governing law",
        "entire agreement",
        "force majeure",
        "intellectual property rights",
    ]
    boilerplate_count = sum(1 for p in boilerplate_phrases if p in text.lower())
    boilerplate_ratio = boilerplate_count / len(boilerplate_phrases)

    # Compute simple bigram uniqueness
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    bigram_counts = Counter(bigrams)
    repeated_bigrams = sum(1 for c in bigram_counts.values() if c > 3)
    bigram_repetition_ratio = repeated_bigrams / max(len(bigram_counts), 1)

    # Score: higher vocab richness and lower boilerplate = more original
    score = int(
        50
        + (vocab_richness - 50) * 0.4
        - boilerplate_ratio * 25
        - bigram_repetition_ratio * 15
    )
    score = max(0, min(100, score))

    if score >= 75:
        verdict = "Original"
    elif score >= 55:
        verdict = "Likely Original"
    elif score >= 35:
        verdict = "Possibly Copied"
    else:
        verdict = "Likely Plagiarized"

    findings = [
        f"Vocabulary richness: {vocab_richness}% unique words out of {total_words} total.",
        f"Boilerplate legal phrases detected: {boilerplate_count} out of {len(boilerplate_phrases)} checked.",
        f"Repeated phrase patterns found: {repeated_bigrams}.",
    ]
    if boilerplate_count >= 5:
        findings.append("High use of standard legal boilerplate language detected.")
    if vocab_richness > 60:
        findings.append("Strong vocabulary variety suggests original authorship.")

    return {
        "originality_score": score,
        "verdict": verdict,
        "findings": findings,
        "document_fingerprint": doc_hash[:16],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Upload a document and return full analysis (summary, risks, originality)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {"error": "Unsupported file type. Please upload PDF, DOCX, or TXT."}
        ), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)

    try:
        text = extract_text(filepath, filename)
    except Exception as exc:
        return jsonify({"error": f"Failed to read document: {str(exc)}"}), 422
    finally:
        # Remove uploaded file after processing
        if os.path.exists(filepath):
            os.remove(filepath)

    if not text.strip():
        return jsonify({"error": "Document appears to be empty or unreadable."}), 422

    # Run all three analyses
    summary = generate_summary(text)
    risks = detect_risks(text)
    originality = check_originality(text)

    return jsonify(
        {
            "filename": filename,
            "word_count": len(text.split()),
            "ai_powered": _openai_client is not None,
            "summary": summary,
            "risk_analysis": risks,
            "originality": originality,
        }
    )


@app.route("/api/voice", methods=["POST"])
def voice():
    """Convert text to speech using gTTS and return an MP3 audio stream.

    Input text is truncated at 2 000 characters to keep audio duration
    reasonable (roughly 2–3 minutes at normal reading speed) and to
    respect gTTS request size limits.
    """
    if not _GTTS_AVAILABLE:
        return jsonify({"error": "gTTS not available on this server."}), 503

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Truncate for reasonable audio length (≈2000 chars ~ 2-3 min)
    text = text[:2000]

    try:
        tts = gTTS(text=text, lang="en", slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return send_file(mp3_fp, mimetype="audio/mpeg", as_attachment=False)
    except Exception as exc:
        return jsonify({"error": f"TTS generation failed: {str(exc)}"}), 500


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "openai_available": _openai_client is not None,
            "gtts_available": _GTTS_AVAILABLE,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
