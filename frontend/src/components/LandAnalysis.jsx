import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, MapPin, User, Hash, Ruler, Calendar, FileText } from 'lucide-react';

const CHECK_ICONS = {
  true:  <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />,
  false: <XCircle className="w-5 h-5 text-red-500 shrink-0" />,
};

const DETAIL_ICONS = {
  owner_name:          <User className="w-4 h-4 text-indigo-500" />,
  survey_number:       <Hash className="w-4 h-4 text-indigo-500" />,
  plot_number:         <Hash className="w-4 h-4 text-indigo-500" />,
  location:            <MapPin className="w-4 h-4 text-indigo-500" />,
  area:                <Ruler className="w-4 h-4 text-indigo-500" />,
  registration_number: <FileText className="w-4 h-4 text-indigo-500" />,
  registration_date:   <Calendar className="w-4 h-4 text-indigo-500" />,
  patta_number:        <Hash className="w-4 h-4 text-indigo-500" />,
};

const DETAIL_LABELS = {
  owner_name:          'Owner / Seller Name',
  survey_number:       'Survey Number',
  plot_number:         'Plot / Flat Number',
  location:            'Location',
  area:                'Land Area',
  registration_number: 'Registration Number',
  registration_date:   'Registration Date',
  patta_number:        'Patta / Khata Number',
};

const SEVERITY_STYLE = {
  high:   'risk-high',
  medium: 'risk-medium',
  low:    'risk-low',
};

export default function LandAnalysis({ landDetails, landValidation }) {
  if (!landDetails && !landValidation) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-lg">No land document detected.</p>
        <p className="text-sm mt-1">Upload a sale deed, encumbrance certificate, or property agreement to see land analysis.</p>
      </div>
    );
  }

  const verdictStyle = {
    low:    'bg-green-50 border-green-200 text-green-800',
    medium: 'bg-amber-50 border-amber-200 text-amber-800',
    high:   'bg-red-50 border-red-200 text-red-800',
  }[landValidation?.level || 'medium'];

  return (
    <div className="space-y-6">
      {/* Extracted Details */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <MapPin className="w-5 h-5 text-indigo-500" />
          Extracted Property Information
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(landDetails || {}).map(([key, value]) => (
            <div key={key} className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                {DETAIL_ICONS[key] || <FileText className="w-4 h-4 text-indigo-500" />}
              </div>
              <div className="min-w-0">
                <p className="text-xs text-gray-500">{DETAIL_LABELS[key] || key}</p>
                <p className={`text-sm font-medium ${value ? 'text-gray-800' : 'text-gray-300 italic'}`}>
                  {value || 'Not found'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legal Validation Checks */}
      {landValidation && (
        <>
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-base font-semibold text-gray-800 mb-4">Legal Validation Checks</h3>
            <div className="space-y-3">
              {Object.entries(landValidation.checks).map(([key, check]) => (
                <div key={key} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-3">
                    {CHECK_ICONS[check.status]}
                    <div>
                      <p className="text-sm font-medium text-gray-800">{check.label}</p>
                      <p className="text-xs text-gray-500">{check.description}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    check.status ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
                  }`}>
                    {check.status ? '✓ Present' : '✗ Missing'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Findings */}
          {landValidation.findings.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-600">Risk Flags</h3>
              {landValidation.findings.map((f, i) => (
                <div key={i} className={`rounded-xl p-4 ${SEVERITY_STYLE[f.severity]}`}>
                  <p className="font-semibold text-gray-800">
                    {f.severity === 'high' ? '🔴' : f.severity === 'medium' ? '🟡' : '🟢'} {f.label}
                  </p>
                  <p className="text-sm text-gray-700 mt-1">{f.reason}</p>
                  <p className="text-sm font-medium text-green-700 mt-2">💡 {f.suggestion}</p>
                </div>
              ))}
            </div>
          )}

          {/* Final Verdict */}
          <div className={`rounded-2xl border p-5 ${verdictStyle}`}>
            <h3 className="font-bold text-base mb-2">
              {landValidation.level === 'low' ? '✅' : landValidation.level === 'medium' ? '⚠️' : '❌'} Final Verdict
            </h3>
            <p className="text-sm leading-relaxed">{landValidation.verdict}</p>
            <p className="mt-3 text-xs opacity-75">
              ℹ️ This is an AI-based document assessment. Always verify with official government records and a qualified legal professional.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
