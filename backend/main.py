"""
LexIntel — AI-Powered Legal & Land Document Intelligence System
Main FastAPI application
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from document_processor import extract_text_from_pdf, detect_document_type
from clause_segmenter import segment_clauses
from risk_analyzer import analyze_risks
from land_extractor import extract_land_details, validate_land_document
import rag_engine
from voice_output import text_to_speech, SUPPORTED_LANGUAGES

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="LexIntel API",
    description="AI-Powered Legal & Land Document Intelligence System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# In-memory document store  (use a DB in production)
# ─────────────────────────────────────────────────────────────────────────────
documents: Dict[str, Dict] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    document_id: str
    question: str


class VoiceRequest(BaseModel):
    text: str
    language: str = "english"


class TranslateRequest(BaseModel):
    text: str
    target_language: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "LexIntel API is running", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "openai_configured": bool(OPENAI_API_KEY),
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document.
    Returns document_id + full analysis (clauses, risks, land details if applicable).
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 20 MB.")

    try:
        text = extract_text_from_pdf(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {exc}") from exc

    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract meaningful text from the PDF. The file may be scanned/image-based.",
        )

    doc_type = detect_document_type(text)
    doc_id = str(uuid.uuid4())

    # Clause segmentation
    clauses = segment_clauses(text)

    # Build RAG index (background-friendly — runs in same thread for simplicity)
    try:
        rag_engine.build_index(doc_id, clauses)
    except Exception as exc:
        logger.warning("RAG index build failed: %s", exc)

    # Risk analysis
    risk_result = analyze_risks(clauses, doc_type)

    # Land-specific analysis
    land_details = None
    land_validation = None
    if doc_type == "land":
        land_details = extract_land_details(text)
        land_validation = validate_land_document(text, land_details)

    doc_record = {
        "id": doc_id,
        "filename": file.filename,
        "doc_type": doc_type,
        "text": text,
        "clauses": clauses,
        "risk": risk_result,
        "land_details": land_details,
        "land_validation": land_validation,
    }
    documents[doc_id] = doc_record

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "doc_type": doc_type,
        "clause_count": len(clauses),
        "clauses": clauses,
        "risk": risk_result,
        "land_details": land_details,
        "land_validation": land_validation,
        "text_preview": text[:500],
    }


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    """Retrieve a previously analysed document."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = documents[document_id]
    # Don't return full text in listing view
    return {k: v for k, v in doc.items() if k != "text"}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Answer a question about the uploaded document using RAG.
    """
    if request.document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found. Please upload it first.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    retrieved = rag_engine.retrieve(request.document_id, request.question, k=4)

    answer_data = await rag_engine.generate_answer(
        question=request.question,
        retrieved=retrieved,
        openai_api_key=OPENAI_API_KEY,
    )

    return {
        "question": request.question,
        "answer": answer_data["answer"],
        "source": answer_data.get("source"),
        "retrieved_clauses": [r["chunk"].get("title") for r in retrieved],
    }


@app.post("/api/voice")
async def voice_output(request: VoiceRequest):
    """
    Convert text to speech in the requested language.
    Returns base64 MP3 audio and the translated text.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    lang = request.language.lower()
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{lang}' not supported. Supported: {list(SUPPORTED_LANGUAGES.keys())}",
        )

    try:
        audio_b64, translated_text = text_to_speech(request.text, request.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "audio_base64": audio_b64,
        "translated_text": translated_text,
        "language": request.language,
        "format": "mp3",
    }


@app.post("/api/translate")
async def translate_text(request: TranslateRequest):
    """Translate text to the target language."""
    from voice_output import _translate, SUPPORTED_LANGUAGES as LANG_MAP

    lang = request.target_language.lower()
    if lang not in LANG_MAP:
        raise HTTPException(status_code=400, detail=f"Language '{lang}' not supported.")

    lang_code = LANG_MAP[lang]
    translated = _translate(request.text, lang_code)
    return {"translated_text": translated, "language": request.target_language}


@app.get("/api/languages")
async def get_languages():
    return {"languages": list(SUPPORTED_LANGUAGES.keys())}
