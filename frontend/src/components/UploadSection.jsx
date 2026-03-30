import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '../api.js';

export default function UploadSection({ onAnalysisComplete }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }

    setError('');
    setLoading(true);
    setProgress(0);

    try {
      const response = await uploadDocument(file, (evt) => {
        if (evt.total) {
          setProgress(Math.round((evt.loaded / evt.total) * 50));
        }
      });
      setProgress(100);
      onAnalysisComplete(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Upload failed. Please try again.';
      setError(detail);
    } finally {
      setLoading(false);
      setProgress(0);
    }
  }, [onAnalysisComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: loading,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 flex flex-col items-center justify-center p-8">
      {/* Hero */}
      <div className="text-center mb-10 max-w-2xl">
        <div className="inline-flex items-center gap-2 bg-indigo-100 text-indigo-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          Powered by RAG + AI
        </div>
        <h2 className="text-4xl font-bold text-gray-900 mb-3">
          Understand Any Legal Document
        </h2>
        <p className="text-lg text-gray-500">
          Upload a contract or land/property document. LexIntel will analyse clauses,
          detect risks, extract key information, and answer your questions — in any language.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          w-full max-w-xl border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive ? 'border-indigo-500 bg-indigo-50 scale-[1.02]' : 'border-gray-300 bg-white hover:border-indigo-400 hover:bg-indigo-50/50'}
          ${loading ? 'opacity-60 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          {loading ? (
            <>
              <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-indigo-600 font-medium">Analysing document… {progress}%</p>
              <p className="text-sm text-gray-400">This may take 10–30 seconds</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-2xl bg-indigo-100 flex items-center justify-center">
                <Upload className="w-8 h-8 text-indigo-600" />
              </div>
              {isDragActive ? (
                <p className="text-indigo-600 font-semibold text-lg">Drop your PDF here…</p>
              ) : (
                <>
                  <p className="text-gray-700 font-semibold text-lg">
                    Drag & drop a PDF, or <span className="text-indigo-600 underline">browse</span>
                  </p>
                  <p className="text-sm text-gray-400">Contracts, Sale Deeds, Agreements, Land Documents — max 20 MB</p>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 max-w-xl w-full">
          <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Feature pills */}
      <div className="mt-10 flex flex-wrap justify-center gap-3">
        {[
          '📋 Clause Segmentation',
          '⚠️ Risk Detection',
          '🏡 Land Validation',
          '💬 AI Chatbot',
          '🔊 Voice Output',
          '🌐 Multilingual',
        ].map((f) => (
          <span key={f} className="bg-white border border-gray-200 text-gray-600 text-sm px-4 py-1.5 rounded-full shadow-sm">
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}
