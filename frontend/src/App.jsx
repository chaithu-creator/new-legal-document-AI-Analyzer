import React, { useState } from 'react';
import Header from './components/Header';
import UploadSection from './components/UploadSection';
import ClauseViewer from './components/ClauseViewer';
import RiskDashboard from './components/RiskDashboard';
import LandAnalysis from './components/LandAnalysis';
import Chatbot from './components/Chatbot';
import VoiceOutput from './components/VoiceOutput';
import {
  FileText, AlertTriangle, MapPin, MessageSquare, Volume2,
  RotateCcw, CheckCircle, Building2
} from 'lucide-react';

const TABS = [
  { id: 'clauses',  label: 'Clauses',      icon: FileText,      show: () => true },
  { id: 'risk',     label: 'Risk',          icon: AlertTriangle, show: () => true },
  { id: 'land',     label: 'Land',          icon: MapPin,        show: (d) => d.doc_type === 'land' },
  { id: 'chat',     label: 'Chatbot',       icon: MessageSquare, show: () => true },
  { id: 'voice',    label: 'Voice',         icon: Volume2,       show: () => true },
];

function DocTypeTag({ docType }) {
  if (docType === 'land') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full">
        <MapPin className="w-3.5 h-3.5" />
        Land Document
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full">
      <Building2 className="w-3.5 h-3.5" />
      Legal Contract
    </span>
  );
}

export default function App() {
  const [analysisData, setAnalysisData] = useState(null);
  const [activeTab, setActiveTab] = useState('clauses');

  const handleAnalysisComplete = (data) => {
    setAnalysisData(data);
    // Auto-select land tab for land documents
    if (data.doc_type === 'land') {
      setActiveTab('land');
    } else {
      setActiveTab('clauses');
    }
  };

  const handleReset = () => {
    setAnalysisData(null);
    setActiveTab('clauses');
  };

  if (!analysisData) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header hasDocument={false} />
        <UploadSection onAnalysisComplete={handleAnalysisComplete} />
      </div>
    );
  }

  const visibleTabs = TABS.filter((t) => t.show(analysisData));

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header hasDocument={true} />

      <div className="max-w-7xl mx-auto w-full px-4 py-6">
        {/* Document info bar */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm px-5 py-4 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-4 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5 text-indigo-500" />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-gray-800 truncate">{analysisData.filename}</p>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <DocTypeTag docType={analysisData.doc_type} />
                <span className="text-xs text-gray-500">{analysisData.clause_count} clauses</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  analysisData.risk?.level === 'high' ? 'bg-red-100 text-red-700' :
                  analysisData.risk?.level === 'medium' ? 'bg-amber-100 text-amber-700' :
                  'bg-green-100 text-green-700'
                }`}>
                  {analysisData.risk?.level === 'high' ? '🔴' : analysisData.risk?.level === 'medium' ? '🟡' : '🟢'} {analysisData.risk?.level?.charAt(0).toUpperCase() + analysisData.risk?.level?.slice(1)} Risk
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600 bg-gray-50 hover:bg-indigo-50 border border-gray-200 hover:border-indigo-200 px-4 py-2 rounded-xl transition-all shrink-0"
          >
            <RotateCcw className="w-4 h-4" />
            Upload New
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 overflow-x-auto">
          {visibleTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all flex-1 justify-center ${
                  activeTab === tab.id
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                {tab.id === 'risk' && analysisData.risk?.summary?.high > 0 && (
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          {activeTab === 'clauses' && (
            <ClauseViewer
              clauses={analysisData.clauses || []}
              riskFindings={analysisData.risk?.findings || []}
            />
          )}
          {activeTab === 'risk' && (
            <RiskDashboard risk={analysisData.risk} />
          )}
          {activeTab === 'land' && (
            <LandAnalysis
              landDetails={analysisData.land_details}
              landValidation={analysisData.land_validation}
            />
          )}
          {activeTab === 'chat' && (
            <Chatbot documentId={analysisData.document_id} />
          )}
          {activeTab === 'voice' && (
            <VoiceOutput analysisData={analysisData} />
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-100 bg-white py-4 text-center text-xs text-gray-400">
        LexIntel v1.0 — AI-based document analysis only. Not official legal advice.
      </footer>
    </div>
  );
}
