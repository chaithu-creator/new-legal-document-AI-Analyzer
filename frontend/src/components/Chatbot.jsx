import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Info } from 'lucide-react';
import { sendChatMessage } from '../api.js';

const SAMPLE_QUESTIONS = [
  'What is the termination clause?',
  'Is there any unlimited liability?',
  'What are the payment terms?',
  'Are there any auto-renewal clauses?',
  'Who are the parties to this agreement?',
  'What is the notice period for termination?',
];

export default function Chatbot({ documentId }) {
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: "Hello! I'm LexIntel AI. Ask me anything about this document — clauses, risks, parties, terms, or anything else.",
      source: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (question) => {
    const q = question || input.trim();
    if (!q || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: q }]);
    setLoading(true);
    try {
      const res = await sendChatMessage(documentId, q);
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: res.data.answer, source: res.data.source },
      ]);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Something went wrong. Please try again.';
      setMessages((prev) => [...prev, { role: 'ai', text: `⚠️ ${errMsg}`, source: null }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="font-semibold text-gray-800">LexIntel Chatbot</p>
          <p className="text-xs text-gray-500">Ask questions about your document</p>
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
          Online
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-indigo-100' : 'bg-indigo-600'
            }`}>
              {msg.role === 'user'
                ? <User className="w-4 h-4 text-indigo-600" />
                : <Bot className="w-4 h-4 text-white" />
              }
            </div>
            <div className={`max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
              <div className={msg.role === 'user' ? 'chat-bubble-user px-4 py-2.5 text-sm' : 'chat-bubble-ai px-4 py-2.5 text-sm'}>
                {msg.text}
              </div>
              {msg.source && (
                <div className="flex items-center gap-1 text-xs text-gray-400 px-1">
                  <Info className="w-3 h-3" />
                  Source: {msg.source}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="chat-bubble-ai px-4 py-3 flex items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
              <span className="text-gray-500">Thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Sample questions */}
      <div className="px-4 py-2 border-t border-gray-50 overflow-x-auto">
        <div className="flex gap-2">
          {SAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              disabled={loading}
              className="text-xs whitespace-nowrap bg-gray-100 hover:bg-indigo-100 text-gray-600 hover:text-indigo-700 px-3 py-1.5 rounded-full transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-100">
        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about the document…"
            disabled={loading}
            className="flex-1 rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading
              ? <Loader2 className="w-4 h-4 text-white animate-spin" />
              : <Send className="w-4 h-4 text-white" />
            }
          </button>
        </form>
      </div>
    </div>
  );
}
