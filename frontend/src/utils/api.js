import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000,
});

// ─── Chat ─────────────────────────────────────────────────────

export const sendChat = (message, sessionId) =>
  api.post('/chat', { message, session_id: sessionId });

export const sendMultiAgent = (message, sessionId, userId, hitlEnabled = false) =>
  api.post('/multi-agent', {
    message,
    session_id: sessionId,
    user_id: userId,
    hitl_enabled: hitlEnabled,
  });

// ─── Health ───────────────────────────────────────────────────

export const getHealth = () => api.get('/health');

// ─── History ──────────────────────────────────────────────────

export const getHistory = (sessionId) => api.get(`/history/${sessionId}`);
export const clearHistory = (sessionId) => api.delete(`/history/${sessionId}`);
export const getSessions = () => api.get('/sessions');

// ─── Facts ────────────────────────────────────────────────────

export const getFacts = (sessionId) =>
  api.get('/facts', { params: sessionId ? { session_id: sessionId } : {} });
export const searchFacts = (query, topK = 5) =>
  api.get('/facts/search', { params: { query, top_k: topK } });
export const saveFact = (fact, category, sessionId) =>
  api.post('/facts', { fact, category, session_id: sessionId });

// ─── Episodes ─────────────────────────────────────────────────

export const getEpisodes = (sessionId) =>
  api.get('/episodes', { params: sessionId ? { session_id: sessionId } : {} });
export const getRecentEpisodes = (limit = 10) =>
  api.get('/episodes/recent', { params: { limit } });
export const searchEpisodes = (query, topK = 5) =>
  api.get('/episodes/search', { params: { query, top_k: topK } });
export const deleteEpisode = (id) => api.delete(`/episodes/${id}`);

// ─── Documents ────────────────────────────────────────────────

export const getDocuments = () => api.get('/documents');
export const uploadPDF = (file, docId) => {
  const form = new FormData();
  form.append('file', file);
  if (docId) form.append('doc_id', docId);
  return api.post('/upload-pdf', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const deleteDocument = (docId) => api.delete(`/documents/${docId}`);
export const searchDocs = (query, topK = 5, mode = 'hybrid', docId) =>
  api.get('/search-docs', { params: { query, top_k: topK, mode, doc_id: docId } });

// ─── Profiles ─────────────────────────────────────────────────

export const getProfile = (userId) => api.get(`/profile/${userId}`);
export const getProfiles = () => api.get('/profiles');
export const updateProfile = (userId, updates) =>
  api.put(`/profile/${userId}`, updates);
export const deleteProfile = (userId) => api.delete(`/profile/${userId}`);

// ─── Memory Management ────────────────────────────────────────

export const getMemoryStats = () => api.get('/memory/stats');
export const runMaintenance = (params) =>
  api.post('/memory/maintenance', null, { params });
export const deduplicateFacts = (sessionId) =>
  api.post('/memory/deduplicate-facts', null, { params: sessionId ? { session_id: sessionId } : {} });
export const summarizeFacts = (sessionId) =>
  api.get(`/memory/summarize-facts/${sessionId}`);
export const getDocumentStats = () => api.get('/memory/document-stats');

// ─── Evaluation ───────────────────────────────────────────────

export const getEvalSummary = () => api.get('/evaluate/summary');
export const getBestRuns = (metric = 'eval_overall', topK = 5) =>
  api.get('/evaluate/best', { params: { metric, top_k: topK } });

// ─── HITL ─────────────────────────────────────────────────────

export const getPendingHITL = () => api.get('/hitl/pending');
export const approveHITL = (requestId, feedback = '') =>
  api.post(`/hitl/${requestId}/approve`, null, { params: { feedback } });
export const rejectHITL = (requestId, feedback = '') =>
  api.post(`/hitl/${requestId}/reject`, null, { params: { feedback } });

export default api;
