import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

export const uploadDocument = (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  });
};

export const sendChatMessage = (documentId, question) =>
  api.post('/api/chat', { document_id: documentId, question });

export const generateVoice = (text, language) =>
  api.post('/api/voice', { text, language });

export const getLanguages = () => api.get('/api/languages');

export const healthCheck = () => api.get('/api/health');

export default api;
