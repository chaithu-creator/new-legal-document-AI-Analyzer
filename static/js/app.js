/* ================================================================
   Legal Document AI Analyzer – Frontend Logic
   ================================================================ */

// ── DOM references ────────────────────────────────────────────────
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const fileInfo       = document.getElementById('fileInfo');
const fileNameEl     = document.getElementById('fileName');
const clearFileBtn   = document.getElementById('clearFile');
const analyzeBtn     = document.getElementById('analyzeBtn');
const analyzeBtnText = document.getElementById('analyzeBtnText');
const analyzeSpinner = document.getElementById('analyzeSpinner');
const results        = document.getElementById('results');
const errorBanner    = document.getElementById('errorBanner');
const aiStatusEl     = document.getElementById('aiStatus');

// Summary
const summaryText    = document.getElementById('summaryText');
const wordCountEl    = document.getElementById('wordCount');
const fileName2El    = document.getElementById('fileName2');
const speakBtn       = document.getElementById('speakBtn');
const stopBtn        = document.getElementById('stopBtn');
const serverVoiceBtn = document.getElementById('serverVoiceBtn');

// Risk
const riskScoreEl    = document.getElementById('riskScore');
const riskLabelEl    = document.getElementById('riskLabel');
const riskListEl     = document.getElementById('riskList');

// Originality
const originalityPct = document.getElementById('originalityPct');
const verdictLabel   = document.getElementById('verdictLabel');
const findingsList   = document.getElementById('findingsList');
const fingerprint    = document.getElementById('fingerprint');

// ── State ────────────────────────────────────────────────────────
let selectedFile    = null;
let currentSummary  = '';
let currentUtterance= null;

// ── Health check on load ─────────────────────────────────────────
fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    if (data.openai_available) {
      aiStatusEl.textContent = '✅ AI-Powered (OpenAI)';
      aiStatusEl.className = 'ai-badge ai-badge--ai';
    } else {
      aiStatusEl.textContent = '⚡ Heuristic Mode';
      aiStatusEl.className = 'ai-badge ai-badge--heuristic';
    }
  })
  .catch(() => {
    aiStatusEl.textContent = '⚠️ Server Offline';
    aiStatusEl.className = 'ai-badge ai-badge--loading';
  });

// ── File selection ───────────────────────────────────────────────
function handleFile(file) {
  if (!file) return;
  const allowed = ['application/pdf',
                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                   'text/plain'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf','docx','txt'].includes(ext)) {
    showError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.');
    return;
  }
  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileInfo.classList.remove('hidden');
  analyzeBtn.disabled = false;
  hideError();
  results.classList.add('hidden');
}

fileInput.addEventListener('change', e => handleFile(e.target.files[0]));

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
});

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drop-zone--active'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('drop-zone--active'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drop-zone--active');
  handleFile(e.dataTransfer.files[0]);
});

clearFileBtn.addEventListener('click', () => {
  selectedFile = null;
  fileInput.value = '';
  fileInfo.classList.add('hidden');
  analyzeBtn.disabled = true;
  results.classList.add('hidden');
  hideError();
});

// ── Analyze ──────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  setLoading(true);
  hideError();
  results.classList.add('hidden');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const resp = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await resp.json();

    if (!resp.ok) {
      showError(data.error || 'Analysis failed. Please try again.');
      return;
    }

    renderResults(data);
  } catch (err) {
    showError('Network error – is the server running?');
  } finally {
    setLoading(false);
  }
});

// ── Render results ───────────────────────────────────────────────
function renderResults(data) {
  // Summary
  currentSummary = data.summary || '';
  summaryText.textContent = currentSummary;
  wordCountEl.textContent = `${data.word_count.toLocaleString()} words`;
  fileName2El.textContent = data.filename;

  // Risk
  const risk = data.risk_analysis || {};
  const score = risk.risk_score ?? 0;
  riskScoreEl.textContent = score;
  const level = risk.overall_risk_level || 'Low';
  riskLabelEl.textContent = level;
  riskLabelEl.style.color = levelColor(level);
  riskScoreEl.style.color = levelColor(level);
  drawGauge(score, level);
  renderRiskList(risk.risks || []);

  // Originality
  const orig = data.originality || {};
  const origScore = orig.originality_score ?? 0;
  originalityPct.textContent = `${origScore}%`;
  verdictLabel.textContent = orig.verdict || '';
  verdictLabel.style.color = verdictColor(orig.verdict);
  findingsList.innerHTML = (orig.findings || [])
    .map(f => `<li>${escapeHtml(f)}</li>`).join('');
  fingerprint.textContent = orig.document_fingerprint || '';
  drawDonut(origScore);

  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRiskList(risks) {
  riskListEl.innerHTML = risks.map(r => `
    <div class="risk-item risk-item--${r.severity}">
      <span class="risk-severity risk-severity--${r.severity}">${escapeHtml(r.severity)}</span>
      <div>
        <p class="risk-category">${escapeHtml(r.category)}</p>
        <p class="risk-desc">${escapeHtml(r.description)}</p>
      </div>
    </div>
  `).join('');
}

// ── Voice (browser Web Speech API) ──────────────────────────────
speakBtn.addEventListener('click', () => {
  if (!('speechSynthesis' in window)) {
    showError('Your browser does not support speech synthesis. Try the 💾 button for audio download.');
    return;
  }
  if (!currentSummary) return;
  window.speechSynthesis.cancel();
  currentUtterance = new SpeechSynthesisUtterance(currentSummary);
  currentUtterance.lang = 'en-US';
  currentUtterance.rate = 0.95;
  currentUtterance.onstart = () => { speakBtn.classList.add('hidden'); stopBtn.classList.remove('hidden'); };
  currentUtterance.onend   = () => { stopBtn.classList.add('hidden'); speakBtn.classList.remove('hidden'); };
  currentUtterance.onerror = () => { stopBtn.classList.add('hidden'); speakBtn.classList.remove('hidden'); };
  window.speechSynthesis.speak(currentUtterance);
});

stopBtn.addEventListener('click', () => {
  window.speechSynthesis.cancel();
  stopBtn.classList.add('hidden');
  speakBtn.classList.remove('hidden');
});

// ── Voice (server gTTS download) ─────────────────────────────────
serverVoiceBtn.addEventListener('click', async () => {
  if (!currentSummary) return;
  serverVoiceBtn.disabled = true;
  serverVoiceBtn.textContent = '⏳';
  try {
    const resp = await fetch('/api/voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: currentSummary }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showError(err.error || 'Voice generation failed on server.');
      return;
    }
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    // Play directly
    const audio = new Audio(url);
    audio.play();
    // Also offer download
    const a = document.createElement('a');
    a.href = url; a.download = 'summary.mp3'; a.click();
  } catch (e) {
    showError('Could not generate server-side audio.');
  } finally {
    serverVoiceBtn.disabled = false;
    serverVoiceBtn.textContent = '💾';
  }
});

// ── Canvas: Risk Gauge ───────────────────────────────────────────
function drawGauge(score, level) {
  const canvas = document.getElementById('riskGauge');
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height - 10;
  const r  = 66;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0);
  ctx.lineWidth = 14;
  ctx.strokeStyle = '#e2e8f0';
  ctx.stroke();

  // Filled arc
  const endAngle = Math.PI + (Math.PI * score / 100);
  const gradient = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
  gradient.addColorStop(0,   '#22c55e');
  gradient.addColorStop(0.5, '#f59e0b');
  gradient.addColorStop(1,   '#dc2626');
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, endAngle);
  ctx.strokeStyle = gradient;
  ctx.stroke();
}

// ── Canvas: Originality Donut ────────────────────────────────────
function drawDonut(score) {
  const canvas = document.getElementById('originalityDonut');
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height / 2;
  const r  = 56;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.lineWidth = 14;
  ctx.strokeStyle = '#e2e8f0';
  ctx.stroke();

  // Score arc
  const startAngle = -Math.PI / 2;
  const endAngle   = startAngle + (2 * Math.PI * score / 100);
  ctx.beginPath();
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.strokeStyle = origColor(score);
  ctx.lineCap = 'round';
  ctx.stroke();
}

// ── Colour helpers ───────────────────────────────────────────────
function levelColor(level) {
  return level === 'High' ? '#dc2626' : level === 'Medium' ? '#d97706' : '#16a34a';
}
function origColor(score) {
  if (score >= 75) return '#16a34a';
  if (score >= 50) return '#2563eb';
  if (score >= 30) return '#d97706';
  return '#dc2626';
}
function verdictColor(verdict) {
  if (!verdict) return '#64748b';
  if (verdict.includes('Original') || verdict === 'Original') return '#16a34a';
  if (verdict.includes('Likely Original')) return '#2563eb';
  if (verdict.includes('Possibly'))  return '#d97706';
  return '#dc2626';
}

// ── UI helpers ───────────────────────────────────────────────────
function setLoading(loading) {
  analyzeBtn.disabled = loading;
  analyzeBtnText.textContent = loading ? 'Analyzing…' : 'Analyze Document';
  analyzeSpinner.classList.toggle('hidden', !loading);
}

function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.classList.remove('hidden');
  errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function hideError() {
  errorBanner.textContent = '';
  errorBanner.classList.add('hidden');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
