# Legal Document AI Analyzer

A real-time web application that analyzes legal documents and provides:

- 📝 **Plain-language summary** – explains complex legalese in simple English
- 🔊 **Voice output** – reads the summary aloud (browser TTS + server-side gTTS)
- ⚠️ **Risk detection** – identifies high/medium/low risk clauses
- 🔍 **Originality check** – estimates document uniqueness with a plagiarism score

Supports **PDF**, **DOCX**, and **TXT** files up to 16 MB.

---

## Features

| Feature | Without OpenAI key | With OpenAI key |
|---------|-------------------|-----------------|
| Summary | First 8 key sentences | GPT-3.5 plain-language summary |
| Risk detection | Keyword heuristics | GPT-3.5 clause analysis |
| Originality check | Text statistics | GPT-3.5 plagiarism analysis |
| Voice output | Browser Web Speech API | gTTS server audio + browser TTS |

---

## Quick Start

### Prerequisites
- Python 3.9+
- (Optional) An [OpenAI API key](https://platform.openai.com/api-keys) for AI-powered analysis

### 1. Clone the repository

```bash
git clone https://github.com/chaithu-creator/new-legal-document-AI-Analyzer.git
cd new-legal-document-AI-Analyzer
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your OpenAI API key (optional but recommended):

```
OPENAI_API_KEY=sk-...your-key-here...
SECRET_KEY=some-random-secret
PORT=5000
```

### 5. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## Production deployment (Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Serve the web UI |
| `POST` | `/api/analyze` | Upload and analyze a document |
| `POST` | `/api/voice` | Convert text to MP3 (gTTS) |
| `GET`  | `/api/health` | Server health / capability check |

### POST `/api/analyze`

**Request** – `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | PDF, DOCX, or TXT document |

**Response** – JSON

```json
{
  "filename": "contract.pdf",
  "word_count": 1234,
  "ai_powered": true,
  "summary": "This agreement is between...",
  "risk_analysis": {
    "overall_risk_level": "High",
    "risk_score": 72,
    "risks": [
      { "category": "Indemnification", "description": "...", "severity": "High" }
    ]
  },
  "originality": {
    "originality_score": 63,
    "verdict": "Likely Original",
    "findings": ["Vocabulary richness: 58.2% unique words..."],
    "document_fingerprint": "a1b2c3d4e5f6a7b8"
  }
}
```

### POST `/api/voice`

**Request** – JSON

```json
{ "text": "This is the text to convert to speech." }
```

**Response** – `audio/mpeg` (MP3 stream)

---

## Project Structure

```
.
├── app.py               # Flask application (backend)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .gitignore
├── templates/
│   └── index.html       # Single-page UI
├── static/
│   ├── css/style.css    # Responsive stylesheet
│   └── js/app.js        # Frontend logic (upload, voice, charts)
└── uploads/             # Temporary upload directory (auto-cleaned)
```

---

## How It Works

1. **Upload** – The user drops a PDF/DOCX/TXT onto the page.
2. **Extract** – The server extracts text using PyPDF2 or python-docx.
3. **Analyze** – Three analyses run in parallel on the server:
   - *Summary*: GPT-3.5 (or fallback sentence extraction)
   - *Risk*: GPT-3.5 clause scan (or keyword heuristics)
   - *Originality*: GPT-3.5 analysis (or vocabulary statistics)
4. **Display** – Results are rendered with colour-coded charts.
5. **Voice** – Click 🔊 to hear the summary via the browser's built-in TTS, or 💾 to generate and download an MP3 from the server.

---

## License

MIT
