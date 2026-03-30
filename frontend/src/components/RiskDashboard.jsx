import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { AlertTriangle, CheckCircle, AlertCircle, Info } from 'lucide-react';

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const SEVERITY_META = {
  high:   { icon: AlertTriangle, color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-red-200',   badge: 'bg-red-100 text-red-700',    label: 'High Risk' },
  medium: { icon: AlertCircle,   color: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-amber-200', badge: 'bg-amber-100 text-amber-700', label: 'Medium Risk' },
  low:    { icon: Info,          color: 'text-blue-600',   bg: 'bg-blue-50',   border: 'border-blue-200',  badge: 'bg-blue-100 text-blue-700',   label: 'Low Risk' },
};

function OverallBadge({ level }) {
  const map = {
    high:   { bg: 'bg-red-100',    text: 'text-red-700',   ring: 'ring-red-300',   emoji: '🔴', label: 'High Risk' },
    medium: { bg: 'bg-amber-100',  text: 'text-amber-700', ring: 'ring-amber-300', emoji: '🟡', label: 'Medium Risk' },
    low:    { bg: 'bg-green-100',  text: 'text-green-700', ring: 'ring-green-300', emoji: '🟢', label: 'Low Risk' },
  };
  const m = map[level] || map.low;
  return (
    <span className={`inline-flex items-center gap-2 ${m.bg} ${m.text} text-lg font-bold px-5 py-2.5 rounded-full ring-2 ${m.ring}`}>
      {m.emoji} {m.label}
    </span>
  );
}

export default function RiskDashboard({ risk }) {
  if (!risk) return null;

  const { level, score, findings, summary } = risk;

  // Doughnut chart
  const doughnutData = {
    labels: ['High Risk', 'Medium Risk', 'Low Risk'],
    datasets: [{
      data: [summary.high, summary.medium, summary.low],
      backgroundColor: ['#ef4444', '#f59e0b', '#22c55e'],
      borderWidth: 0,
      hoverOffset: 4,
    }],
  };

  // Bar chart by finding
  const findingLabels = findings.slice(0, 8).map((f) => f.label.length > 20 ? f.label.substring(0, 20) + '…' : f.label);
  const findingScores = findings.slice(0, 8).map((f) => f.score);
  const barColors = findings.slice(0, 8).map((f) =>
    f.severity === 'high' ? '#ef4444' : f.severity === 'medium' ? '#f59e0b' : '#22c55e'
  );

  const barData = {
    labels: findingLabels,
    datasets: [{
      label: 'Risk Score',
      data: findingScores,
      backgroundColor: barColors,
      borderRadius: 6,
    }],
  };

  return (
    <div className="space-y-6">
      {/* Overall summary */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Overall Risk Assessment</h3>
            <p className="text-sm text-gray-500 mt-1">Total risk score: <strong>{score}</strong> · {summary.total} issue{summary.total !== 1 ? 's' : ''} found</p>
          </div>
          <OverallBadge level={level} />
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6">
          {[
            { key: 'high', label: 'High', color: 'text-red-600', bg: 'bg-red-50' },
            { key: 'medium', label: 'Medium', color: 'text-amber-600', bg: 'bg-amber-50' },
            { key: 'low', label: 'Low', color: 'text-green-600', bg: 'bg-green-50' },
          ].map(({ key, label, color, bg }) => (
            <div key={key} className={`${bg} rounded-xl p-4 text-center`}>
              <p className={`text-3xl font-bold ${color}`}>{summary[key]}</p>
              <p className="text-xs text-gray-500 mt-1">{label} Risk</p>
            </div>
          ))}
        </div>
      </div>

      {/* Charts */}
      {summary.total > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h4 className="text-sm font-semibold text-gray-600 mb-4">Risk Distribution</h4>
            <div className="h-48 flex items-center justify-center">
              <Doughnut
                data={doughnutData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
                }}
              />
            </div>
          </div>

          {findings.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h4 className="text-sm font-semibold text-gray-600 mb-4">Risk by Finding</h4>
              <div className="h-48">
                <Bar
                  data={barData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                      x: { ticks: { font: { size: 9 } } },
                      y: { beginAtZero: true, ticks: { stepSize: 1 } },
                    },
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Individual findings */}
      {findings.length === 0 ? (
        <div className="bg-green-50 rounded-2xl p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <p className="text-green-700 font-semibold text-lg">No Risk Patterns Detected</p>
          <p className="text-green-600 text-sm mt-1">This document appears to be well-structured.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-600">Detailed Findings</h3>
          {findings.map((finding, i) => {
            const meta = SEVERITY_META[finding.severity] || SEVERITY_META.low;
            const Icon = meta.icon;
            return (
              <div key={i} className={`rounded-xl border p-4 ${meta.bg} ${meta.border}`}>
                <div className="flex items-start gap-3">
                  <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${meta.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`text-sm font-semibold ${meta.color}`}>{finding.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${meta.badge}`}>
                        {meta.label}
                      </span>
                      {finding.clause_title && (
                        <span className="text-xs text-gray-500">— {finding.clause_title}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700">{finding.reason}</p>
                    {finding.matched_text && (
                      <p className="text-xs text-gray-500 italic mt-1 bg-white/60 rounded px-2 py-1">
                        "…{finding.matched_text}…"
                      </p>
                    )}
                    <p className="text-sm text-green-700 font-medium mt-2">
                      💡 Suggestion: {finding.suggestion}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
