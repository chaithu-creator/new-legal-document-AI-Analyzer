import React, { useState, useRef } from 'react';
import { Volume2, Globe, Loader2, Play, Pause, Download, FileText } from 'lucide-react';
import { generateVoice } from '../api.js';

const LANGUAGES = [
  { id: 'english',   flag: '🇬🇧', name: 'English' },
  { id: 'hindi',     flag: '🇮🇳', name: 'Hindi' },
  { id: 'telugu',    flag: '🇮🇳', name: 'Telugu' },
  { id: 'tamil',     flag: '🇮🇳', name: 'Tamil' },
  { id: 'kannada',   flag: '🇮🇳', name: 'Kannada' },
  { id: 'malayalam', flag: '🇮🇳', name: 'Malayalam' },
  { id: 'marathi',   flag: '🇮🇳', name: 'Marathi' },
  { id: 'bengali',   flag: '🇮🇳', name: 'Bengali' },
  { id: 'gujarati',  flag: '🇮🇳', name: 'Gujarati' },
  { id: 'punjabi',   flag: '🇮🇳', name: 'Punjabi' },
  { id: 'urdu',      flag: '🇵🇰', name: 'Urdu' },
  { id: 'french',    flag: '🇫🇷', name: 'French' },
  { id: 'german',    flag: '🇩🇪', name: 'German' },
  { id: 'spanish',   flag: '🇪🇸', name: 'Spanish' },
  { id: 'arabic',    flag: '🇸🇦', name: 'Arabic' },
  { id: 'chinese',   flag: '🇨🇳', name: 'Chinese' },
  { id: 'japanese',  flag: '🇯🇵', name: 'Japanese' },
  { id: 'korean',    flag: '🇰🇷', name: 'Korean' },
];

const PRESET_TEXTS = [
  { label: 'Risk Summary', key: 'risk' },
  { label: 'Clause Overview', key: 'clauses' },
  { label: 'Land Summary', key: 'land' },
  { label: 'Custom Text', key: 'custom' },
];

function buildPresetText(key, analysisData) {
  if (key === 'risk' && analysisData?.risk) {
    const r = analysisData.risk;
    const findings = r.findings.slice(0, 3).map((f) => `${f.label}: ${f.reason}`).join('. ');
    return `Overall risk level is ${r.level}. Risk score is ${r.score}. ${r.summary.high} high risk issues, ${r.summary.medium} medium risk issues, ${r.summary.low} low risk issues were found. ${findings}`;
  }
  if (key === 'clauses' && analysisData?.clauses) {
    const count = analysisData.clauses.length;
    const labels = [...new Set(analysisData.clauses.map((c) => c.label))].join(', ');
    return `This document contains ${count} clauses. The clause types identified are: ${labels}.`;
  }
  if (key === 'land' && analysisData?.land_details) {
    const d = analysisData.land_details;
    const v = analysisData.land_validation;
    let t = 'Property details: ';
    if (d.owner_name) t += `Owner is ${d.owner_name}. `;
    if (d.location) t += `Located at ${d.location}. `;
    if (d.area) t += `Area is ${d.area}. `;
    if (v) t += `Validation result: ${v.verdict}`;
    return t;
  }
  return '';
}

export default function VoiceOutput({ analysisData }) {
  const [selectedLang, setSelectedLang] = useState('english');
  const [selectedPreset, setSelectedPreset] = useState('risk');
  const [customText, setCustomText] = useState('');
  const [loading, setLoading] = useState(false);
  const [audioSrc, setAudioSrc] = useState(null);
  const [translatedText, setTranslatedText] = useState('');
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const audioRef = useRef(null);

  const handleGenerate = async () => {
    const textToSpeak = selectedPreset === 'custom'
      ? customText.trim()
      : buildPresetText(selectedPreset, analysisData);

    if (!textToSpeak) {
      setError('No text available for this option. Try selecting another preset or entering custom text.');
      return;
    }
    setError('');
    setLoading(true);
    setAudioSrc(null);
    setTranslatedText('');
    try {
      const res = await generateVoice(textToSpeak, selectedLang);
      const { audio_base64, translated_text } = res.data;
      setAudioSrc(`data:audio/mp3;base64,${audio_base64}`);
      setTranslatedText(translated_text);
    } catch (err) {
      setError(err.response?.data?.detail || 'Voice generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  const downloadAudio = () => {
    if (!audioSrc) return;
    const a = document.createElement('a');
    a.href = audioSrc;
    a.download = `lexintel-voice-${selectedLang}.mp3`;
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* Language selector */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-indigo-500" />
          Select Output Language
        </h3>
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.id}
              onClick={() => setSelectedLang(lang.id)}
              className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all text-xs font-medium ${
                selectedLang === lang.id
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                  : 'border-gray-100 bg-gray-50 text-gray-600 hover:border-indigo-200'
              }`}
            >
              <span className="text-xl">{lang.flag}</span>
              {lang.name}
            </button>
          ))}
        </div>
      </div>

      {/* Content selector */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-500" />
          What to Speak?
        </h3>
        <div className="flex flex-wrap gap-2 mb-4">
          {PRESET_TEXTS.map((p) => (
            <button
              key={p.key}
              onClick={() => setSelectedPreset(p.key)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                selectedPreset === p.key
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-indigo-300'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {selectedPreset === 'custom' ? (
          <textarea
            rows={4}
            placeholder="Type or paste any text to convert to speech…"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
          />
        ) : (
          <div className="bg-gray-50 rounded-xl px-4 py-3 text-sm text-gray-600 min-h-[60px]">
            {buildPresetText(selectedPreset, analysisData) || (
              <span className="text-gray-300 italic">No content available for this preset.</span>
            )}
          </div>
        )}
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full flex items-center justify-center gap-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 rounded-2xl text-base transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {loading
          ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating voice…</>
          : <><Volume2 className="w-5 h-5" /> 🔊 Generate Voice in {LANGUAGES.find((l) => l.id === selectedLang)?.name}</>
        }
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Audio player */}
      {audioSrc && (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl border border-indigo-100 p-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={togglePlay}
              className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center hover:bg-indigo-700 transition-colors"
            >
              {playing
                ? <Pause className="w-5 h-5 text-white" />
                : <Play className="w-5 h-5 text-white ml-0.5" />
              }
            </button>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800">
                Voice Output — {LANGUAGES.find((l) => l.id === selectedLang)?.name}
              </p>
              <p className="text-xs text-gray-500">Click play to listen</p>
            </div>
            <button
              onClick={downloadAudio}
              className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>

          <audio
            ref={audioRef}
            src={audioSrc}
            onEnded={() => setPlaying(false)}
            className="w-full"
            controls
          />

          {translatedText && selectedLang !== 'english' && (
            <div className="mt-4 bg-white rounded-xl p-4 border border-indigo-100">
              <p className="text-xs text-gray-500 mb-1">Translated text ({LANGUAGES.find((l) => l.id === selectedLang)?.name}):</p>
              <p className="text-sm text-gray-700 leading-relaxed">{translatedText}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
