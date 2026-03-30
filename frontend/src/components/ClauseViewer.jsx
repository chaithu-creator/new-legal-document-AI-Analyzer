import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Tag } from 'lucide-react';

const LABEL_META = {
  termination:          { color: 'bg-red-100 text-red-700',      dot: 'bg-red-500',    name: 'Termination' },
  liability:            { color: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500', name: 'Liability' },
  payment:              { color: 'bg-blue-100 text-blue-700',     dot: 'bg-blue-500',   name: 'Payment' },
  confidentiality:      { color: 'bg-purple-100 text-purple-700', dot: 'bg-purple-500', name: 'Confidentiality' },
  intellectual_property:{ color: 'bg-pink-100 text-pink-700',     dot: 'bg-pink-500',   name: 'IP Rights' },
  dispute_resolution:   { color: 'bg-teal-100 text-teal-700',     dot: 'bg-teal-500',   name: 'Dispute Resolution' },
  warranties:           { color: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500', name: 'Warranties' },
  auto_renewal:         { color: 'bg-red-100 text-red-700',       dot: 'bg-red-500',    name: 'Auto-Renewal' },
  penalty:              { color: 'bg-red-100 text-red-700',       dot: 'bg-red-600',    name: 'Penalty' },
  general:              { color: 'bg-gray-100 text-gray-600',     dot: 'bg-gray-400',   name: 'General' },
};

function ClauseCard({ clause, riskFindings }) {
  const [expanded, setExpanded] = useState(false);
  const meta = LABEL_META[clause.label] || LABEL_META.general;
  const clauseRisks = riskFindings.filter((f) => f.clause_id === clause.id);

  return (
    <div className={`bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden clause-${clause.label}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-gray-400 text-sm font-mono w-6 shrink-0">{clause.id}</span>
          <span className="font-medium text-gray-800 truncate">{clause.title}</span>
        </div>
        <div className="flex items-center gap-2 ml-3 shrink-0">
          {clauseRisks.length > 0 && (
            <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium">
              ⚠ {clauseRisks.length} risk{clauseRisks.length > 1 ? 's' : ''}
            </span>
          )}
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1 ${meta.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`}></span>
            {meta.name}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-gray-50">
          <p className="text-sm text-gray-600 leading-relaxed mt-3 whitespace-pre-wrap">{clause.text}</p>

          {clauseRisks.length > 0 && (
            <div className="mt-4 space-y-2">
              {clauseRisks.map((risk, i) => (
                <div key={i} className={`rounded-lg p-3 text-sm risk-${risk.severity}`}>
                  <p className="font-semibold text-gray-800">⚠ {risk.label}</p>
                  <p className="text-gray-600 mt-1">{risk.reason}</p>
                  {risk.matched_text && (
                    <p className="mt-1 text-xs text-gray-500 italic">
                      "…{risk.matched_text}…"
                    </p>
                  )}
                  <p className="mt-1.5 text-xs font-medium text-green-700">
                    💡 {risk.suggestion}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ClauseViewer({ clauses, riskFindings }) {
  const [filter, setFilter] = useState('all');
  const labels = ['all', ...new Set(clauses.map((c) => c.label))];
  const filtered = filter === 'all' ? clauses : clauses.filter((c) => c.label === filter);

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-4">
        {labels.map((l) => (
          <button
            key={l}
            onClick={() => setFilter(l)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
              filter === l
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
            }`}
          >
            {l === 'all' ? `All (${clauses.length})` : (LABEL_META[l]?.name || l)}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-8">No clauses match this filter.</p>
        ) : (
          filtered.map((clause) => (
            <ClauseCard
              key={clause.id}
              clause={clause}
              riskFindings={riskFindings || []}
            />
          ))
        )}
      </div>
    </div>
  );
}
