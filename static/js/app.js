/* ================================================================
   AI Legal Risk Analyzer – Frontend Logic
   ================================================================ */

'use strict';

// ── DOM references ────────────────────────────────────────────────

// Upload
const dropZone       = document.getElementById('dropZone');
const fileInput      = document.getElementById('fileInput');
const fileInfo       = document.getElementById('fileInfo');
const fileNameEl     = document.getElementById('fileName');
const clearFileBtn   = document.getElementById('clearFile');
const urlInput       = document.getElementById('urlInput');
const analyzeBtn     = document.getElementById('analyzeBtn');
const analyzeBtnText = document.getElementById('analyzeBtnText');
const analyzeSpinner = document.getElementById('analyzeSpinner');
const regionSelect   = document.getElementById('regionSelect');

// Tabs
const tabBtns        = document.querySelectorAll('.tab-btn');
const tabFile        = document.getElementById('tabFile');
const tabUrl         = document.getElementById('tabUrl');

// AI status
const aiStatusEl     = document.getElementById('aiStatus');

// Results
const results        = document.getElementById('results');
const errorBanner    = document.getElementById('errorBanner');
const metaFile       = document.getElementById('metaFile');
const metaWords      = document.getElementById('metaWords');
const metaRegion     = document.getElementById('metaRegion');
const metaAI         = document.getElementById('metaAI');
const downloadBtn    = document.getElementById('downloadBtn');

// Risk hero
const riskScoreEl    = document.getElementById('riskScore');
const riskLabelEl    = document.getElementById('riskLabel');
const riskCaptionEl  = document.getElementById('riskCaption');

// Summary
const summaryText    = document.getElementById('summaryText');
const speakBtn       = document.getElementById('speakBtn');
const stopBtn        = document.getElementById('stopBtn');
const serverVoiceBtn = document.getElementById('serverVoiceBtn');

// Risk list
const riskListEl     = document.getElementById('riskList');

// Violations
const violationsList = document.getElementById('violationsList');
const complianceBadge= document.getElementById('complianceScore');

// Simplify
const simplifyList   = document.getElementById('simplifyList');

// Originality
const originalityPct = document.getElementById('originalityPct');
const verdictLabel   = document.getElementById('verdictLabel');
const findingsList   = document.getElementById('findingsList');
const fingerprint    = document.getElementById('fingerprint');

// Chatbot
const chatToggle     = document.getElementById('chatToggle');
const chatPanel      = document.getElementById('chatPanel');
const chatClose      = document.getElementById('chatClose');
const chatInput      = document.getElementById('chatInput');
const chatSend       = document.getElementById('chatSend');
const chatMessages   = document.getElementById('chatMessages');
const chatModeEl     = document.getElementById('chatMode');

// ── State ────────────────────────────────────────────────────────
let selectedFile    = null;
let activeTab       = 'file';
let currentSummary  = '';
let currentUtterance= null;
let currentSessionId= null;
let chatHistory     = [];

// ── Health check on load ─────────────────────────────────────────
fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    if (data.openai_available) {
      aiStatusEl.textContent = '✅ AI-Powered';
      aiStatusEl.className   = 'ai-badge ai-badge--ai';
    } else {
      aiStatusEl.textContent = '⚡ Heuristic Mode';
      aiStatusEl.className   = 'ai-badge ai-badge--heuristic';
    }
  })
  .catch(() => {
    aiStatusEl.textContent = '⚠️ Server Offline';
    aiStatusEl.className   = 'ai-badge ai-badge--loading';
  });

// ── Tab switching ─────────────────────────────────────────────────
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => { b.classList.remove('tab-btn--active'); b.setAttribute('aria-selected','false'); });
    btn.classList.add('tab-btn--active');
    btn.setAttribute('aria-selected','true');
    activeTab = btn.dataset.tab;
    tabFile.classList.toggle('hidden', activeTab !== 'file');
    tabUrl.classList.toggle('hidden',  activeTab !== 'url');
    updateAnalyzeBtn();
    hideError();
  });
});

// ── File selection ───────────────────────────────────────────────
function handleFile(file) {
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  const allowed = ['pdf','docx','txt','jpg','jpeg','png','gif','bmp','tiff','tif','webp'];
  if (!allowed.includes(ext)) {
    showError('Unsupported file type. Please upload a PDF, DOCX, TXT, or image file.');
    return;
  }
  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileInfo.classList.remove('hidden');
  updateAnalyzeBtn();
  hideError();
  results.classList.add('hidden');
}

fileInput.addEventListener('change', e => handleFile(e.target.files[0]));
dropZone.addEventListener('click',   () => fileInput.click());
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
  updateAnalyzeBtn();
  results.classList.add('hidden');
  hideError();
});

urlInput.addEventListener('input', updateAnalyzeBtn);

function updateAnalyzeBtn() {
  if (activeTab === 'file') {
    analyzeBtn.disabled = !selectedFile;
  } else {
    analyzeBtn.disabled = !urlInput.value.trim();
  }
}

// ── Analyze ──────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
  setLoading(true);
  hideError();
  results.classList.add('hidden');

  const formData = new FormData();
  formData.append('region', regionSelect.value);

  if (activeTab === 'file') {
    if (!selectedFile) { setLoading(false); return; }
    formData.append('file', selectedFile);
  } else {
    const url = urlInput.value.trim();
    if (!url) { setLoading(false); return; }
    formData.append('url', url);
  }

  try {
    const resp = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await resp.json();
    if (!resp.ok) {
      showError(data.error || 'Analysis failed. Please try again.');
      return;
    }
    currentSessionId = data.session_id || null;
    chatHistory      = [];
    updateChatMode(data.filename || '');
    renderResults(data);
  } catch {
    showError('Network error – is the server running?');
  } finally {
    setLoading(false);
  }
});

// ── Render results ───────────────────────────────────────────────
function renderResults(data) {
  // Meta bar
  metaFile.textContent   = '📄 ' + (data.filename || 'document');
  metaWords.textContent  = '📝 ' + (data.word_count || 0).toLocaleString() + ' words';
  metaRegion.textContent = '📍 ' + (data.region || 'India');
  metaAI.textContent     = data.ai_powered ? '🤖 AI-Powered' : '⚡ Heuristic';

  // Download button
  if (data.annotated_available && data.session_id) {
    downloadBtn.classList.remove('hidden');
    downloadBtn.onclick = () => {
      window.location.href = `/api/download/${data.session_id}`;
    };
  } else {
    downloadBtn.classList.add('hidden');
  }

  // Risk hero
  const risk  = data.risk_analysis || {};
  const score = risk.risk_score ?? 0;
  const level = risk.overall_risk_level || 'Low';
  riskScoreEl.textContent = score;
  riskScoreEl.style.color = levelColor(level);
  riskLabelEl.textContent = level + ' Risk';
  riskLabelEl.style.color = levelColor(level);
  riskCaptionEl.textContent = riskCaption(level, score);
  drawGauge(score, level);

  // Summary
  currentSummary   = data.summary || '';
  summaryText.textContent = currentSummary;

  // Risk list
  renderRiskList(risk.risks || []);

  // Rule violations
  renderViolations(data.violations || {});

  // Simplified clauses
  renderSimplified(data.simplified_clauses || []);

  // Originality
  const orig     = data.originality || {};
  const origScore= orig.originality_score ?? 0;
  originalityPct.textContent = origScore + '%';
  verdictLabel.textContent   = orig.verdict || '';
  verdictLabel.style.color   = verdictColor(orig.verdict);
  findingsList.innerHTML = (orig.findings || []).map(f => `<li>${escapeHtml(f)}</li>`).join('');
  fingerprint.textContent    = orig.document_fingerprint || '';
  drawDonut(origScore);

  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function riskCaption(level, score) {
  if (level === 'High')   return `High risk detected (${score}/100). Review carefully before signing.`;
  if (level === 'Medium') return `Moderate risk (${score}/100). Some clauses need attention.`;
  return `Low risk (${score}/100). Appears relatively safe, but always review.`;
}

function renderRiskList(risks) {
  riskListEl.innerHTML = risks.map(r => `
    <div class="risk-item risk-item--${r.severity || 'Low'}">
      <span class="risk-severity risk-severity--${r.severity || 'Low'}">${escapeHtml(r.severity || 'Low')}</span>
      <div>
        <p class="risk-category">${escapeHtml(r.category || '')}</p>
        <p class="risk-desc">${escapeHtml(r.description || '')}</p>
      </div>
    </div>
  `).join('');
}

function renderViolations(violationsData) {
  const list   = violationsData.violations || [];
  const cscore = violationsData.compliance_score ?? 100;

  // Compliance badge colour
  let badgeBg = '#f0fdf4', badgeColor = '#16a34a', badgeBorder = '#bbf7d0';
  if (cscore < 50) { badgeBg = '#fef2f2'; badgeColor = '#dc2626'; badgeBorder = '#fecaca'; }
  else if (cscore < 80) { badgeBg = '#fffbeb'; badgeColor = '#d97706'; badgeBorder = '#fde68a'; }
  complianceBadge.textContent = `Compliance: ${cscore}/100`;
  complianceBadge.style.cssText = `background:${badgeBg};color:${badgeColor};border-color:${badgeBorder}`;

  if (!list.length) {
    violationsList.innerHTML = '<p class="no-violations">✅ No specific rule violations detected.</p>';
    return;
  }
  violationsList.innerHTML = list.map(v => `
    <div class="violation-item">
      <p class="violation-rule">⚖ ${escapeHtml(v.rule || 'Unknown Rule')}</p>
      ${v.clause ? `<p class="violation-clause">${escapeHtml(v.clause)}</p>` : ''}
      <p class="violation-issue">${escapeHtml(v.issue || '')}</p>
      ${v.suggestion ? `<div class="violation-suggestion"><strong>💡 Suggestion</strong>${escapeHtml(v.suggestion)}</div>` : ''}
    </div>
  `).join('');
}

function renderSimplified(items) {
  if (!items.length) {
    simplifyList.innerHTML = '<p style="color:var(--color-muted);font-size:.875rem">No complex clauses detected, or simplification was not available.</p>';
    return;
  }
  simplifyList.innerHTML = items.map(item => `
    <div class="simplify-item">
      <div class="simplify-original">📜 "${escapeHtml(item.original || '')}"</div>
      <div class="simplify-arrow">↓</div>
      <div class="simplify-plain">✅ ${escapeHtml(item.simplified || '')}</div>
    </div>
  `).join('');
}

// ── Voice (browser Web Speech API) ──────────────────────────────
speakBtn.addEventListener('click', () => {
  if (!('speechSynthesis' in window)) {
    showError('Your browser does not support speech synthesis. Try the 💾 button.');
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
      showError(err.error || 'Voice generation failed.');
      return;
    }
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    new Audio(url).play();
    const a = document.createElement('a');
    a.href = url; a.download = 'summary.mp3'; a.click();
  } catch {
    showError('Could not generate server-side audio.');
  } finally {
    serverVoiceBtn.disabled = false;
    serverVoiceBtn.textContent = '💾';
  }
});

// ── Chatbot ──────────────────────────────────────────────────────
function updateChatMode(filename) {
  if (filename) {
    chatModeEl.textContent = `Document Mode: ${filename.slice(0, 30)}`;
  } else {
    chatModeEl.textContent = 'General Mode';
  }
}

chatToggle.addEventListener('click', () => {
  const isHidden = chatPanel.hasAttribute('hidden');
  if (isHidden) {
    chatPanel.removeAttribute('hidden');
    chatInput.focus();
  } else {
    chatPanel.setAttribute('hidden', '');
  }
});

chatClose.addEventListener('click', () => chatPanel.setAttribute('hidden', ''));

chatSend.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
});

async function sendChatMessage() {
  const msg = chatInput.value.trim();
  if (!msg) return;

  chatInput.value = '';
  appendChatMsg(msg, 'user');

  // Typing indicator
  const typingEl = appendTyping();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message:      msg,
        session_id:   currentSessionId || '',
        chat_history: chatHistory,
        region:       regionSelect.value,
      }),
    });
    const data = await resp.json();
    typingEl.remove();
    const reply = data.reply || data.error || 'Sorry, I could not respond right now.';
    appendChatMsg(reply, 'bot');
    chatHistory.push({ role: 'user',      content: msg   });
    chatHistory.push({ role: 'assistant', content: reply });
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
  } catch {
    typingEl.remove();
    appendChatMsg('Sorry, there was a network error.', 'bot');
  }
}

function appendChatMsg(text, role) {
  const div = document.createElement('div');
  div.className = `chat-msg chat-msg--${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.textContent = text;
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'chat-msg chat-msg--bot chat-typing';
  div.innerHTML = '<div class="chat-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

// ── Canvas: Risk Gauge ───────────────────────────────────────────
function drawGauge(score, level) {
  const canvas = document.getElementById('riskGauge');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height - 12;
  const r  = 70;
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
  ctx.lineWidth = 14;
  ctx.strokeStyle = gradient;
  ctx.lineCap = 'round';
  ctx.stroke();
}

// ── Canvas: Originality Donut ────────────────────────────────────
function drawDonut(score) {
  const canvas = document.getElementById('originalityDonut');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height / 2;
  const r  = 56;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.lineWidth = 14;
  ctx.strokeStyle = '#e2e8f0';
  ctx.stroke();

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
  if (verdict === 'Original' || verdict.startsWith('Original')) return '#16a34a';
  if (verdict.includes('Likely Original')) return '#2563eb';
  if (verdict.includes('Possibly'))        return '#d97706';
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
