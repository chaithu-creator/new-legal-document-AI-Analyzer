# LexIntel — AI-Powered Legal & Land Document Intelligence System

> **Disclaimer:** LexIntel performs AI-based document analysis only. It is **not** an official legal authority and does not replace qualified legal advice.

---

## 🎯 Overview

LexIntel is a full-stack AI system that helps users understand, analyse, and query legal and land/property documents. It uses a **Retrieval-Augmented Generation (RAG)** architecture to deliver:

| Feature | Description |
|---|---|
| 📋 **Clause Segmentation** | Splits documents into labelled clauses (Termination, Liability, Payment, etc.) |
| ⚠️ **Risk Analysis** | Detects risky patterns with severity scores and improvement suggestions |
| 🏡 **Land Document Analysis** | Extracts property details and validates legal completeness |
| 💬 **AI Chatbot** | Ask any question about the document; answers cite the source clause |
| 🔊 **Voice Output** | Converts analysis to speech in 12+ languages including Hindi & Telugu |
| 🌐 **Multilingual** | English, Hindi, Telugu, Tamil, Kannada, French, Spanish, and more |

---

## 🏗️ Architecture

```
User (Upload PDF)
      ↓
FastAPI Backend
      ↓
Document Processor (PyMuPDF)
      ↓
Clause Segmenter (Rule-based NLP)
      ↓
FAISS Vector Index (sentence-transformers / TF-IDF fallback)
      ↓
┌─────────────────────────────────────────────┐
│  Risk Analyser  │  Land Extractor  │  RAG   │
└─────────────────────────────────────────────┘
      ↓
Output Layer:
  - JSON API → React Frontend
  - Voice (gTTS + deep-translator)
  - Charts (Chart.js)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11, PyMuPDF, FAISS, sentence-transformers, scikit-learn |
| LLM (optional) | OpenAI GPT-3.5-turbo |
| Voice | gTTS, deep-translator (Google Translate) |
| Frontend | React 18, Chart.js, lucide-react, react-dropzone |
| Styling | Tailwind CSS (CDN) |
| Container | Docker, docker-compose |

---

## 🚀 Quick Start

### Option A — Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/chaithu-creator/new-legal-document-AI-Analyzer.git
cd new-legal-document-AI-Analyzer

# 2. Configure environment (optional — works without OpenAI key)
cp backend/.env.example backend/.env
# Edit backend/.env and add OPENAI_API_KEY=sk-... (optional)

# 3. Start everything
docker-compose up --build

# App:     http://localhost:3000
# API:     http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

### Option B — Manual

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: add OpenAI key
cp .env.example .env
# edit .env → OPENAI_API_KEY=sk-...

uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm start           # Opens http://localhost:3000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload PDF; returns full analysis |
| POST | `/api/chat` | Ask a question about a document |
| POST | `/api/voice` | Generate MP3 voice output |
| POST | `/api/translate` | Translate text to any supported language |
| GET  | `/api/languages` | List supported languages |
| GET  | `/api/health` | Health check |
| GET  | `/docs` | Interactive Swagger UI |

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Enables GPT-powered chat. Works without it (uses extractive QA) |
| `REACT_APP_API_URL` | `http://localhost:8000` | Backend URL for the frontend |

---

## 🔍 How Risk Scoring Works

```
+2  Unlimited liability clause detected
+2  No termination clause
+2  Unilateral modification rights
+2  Broad indemnity clause
+1  Auto-renewal trap
+1  Penalty-heavy terms
+1  One-sided termination
+1  Vague / discretionary language
+1  Missing dispute resolution
+1  Missing confidentiality clause

Score 0–1 → 🟢 Low Risk
Score 2–3 → 🟡 Medium Risk
Score 4+  → 🔴 High Risk
```

---

## 🏡 Land Document Validation Logic

```
IF owner present AND registration present → ✅ OK
IF encumbrance not mentioned             → ⚠️ Medium Risk
IF approval authority missing            → 🔴 High Risk
IF survey number missing                 → ⚠️ Medium Risk
```

---

## ⚠️ Limitations

- Not a legal authority — always consult a qualified lawyer
- Depends on document quality (scanned/image PDFs not supported)
- Cannot verify against government databases
- AI analysis may have minor errors
- Voice output requires internet access (Google TTS)
