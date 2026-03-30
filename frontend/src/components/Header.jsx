import React from 'react';
import { Scale, Brain, Zap } from 'lucide-react';

export default function Header({ hasDocument }) {
  return (
    <header className="gradient-bg text-white shadow-2xl">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
            <Scale className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">LexIntel</h1>
            <p className="text-xs text-indigo-200 -mt-0.5">AI Legal Document Intelligence</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-6 text-sm text-indigo-200">
          <div className="flex items-center gap-1.5">
            <Brain className="w-4 h-4" />
            <span>RAG-Powered</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="w-4 h-4" />
            <span>Real-time Analysis</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-xs bg-white/10 text-white px-3 py-1 rounded-full border border-white/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Live
          </span>
        </div>
      </div>

      {/* Disclaimer banner */}
      <div className="bg-amber-500/20 border-t border-amber-400/30 text-amber-200 text-center text-xs py-1.5 px-4">
        ⚠️ AI-based document analysis only — not official legal advice or verification. Always consult a qualified legal professional.
      </div>
    </header>
  );
}
