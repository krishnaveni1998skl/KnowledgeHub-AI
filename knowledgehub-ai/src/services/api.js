/**
 * Centralized API client for KnowledgeHub AI Backend.
 * Handles HTTP requests, authentication tokens, file uploads, and multilingual RAG queries.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const TOKEN_KEY = "knowledgehub_token";
const USER_KEY = "knowledgehub_user";

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || null;
}

function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveAuth(token, user, remember = true) {
  const storage = remember ? localStorage : sessionStorage;
  // Clear any existing from opposite storage
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);

  if (token) storage.setItem(TOKEN_KEY, token);
  if (user) storage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

function getAuthHeaders(extraHeaders = {}) {
  const token = getStoredToken();
  const headers = { ...extraHeaders };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = "Network request failed.";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText || `HTTP Error ${response.status}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  baseUrl: API_BASE,

  // Token & User session helpers
  getToken: getStoredToken,
  getUser: getStoredUser,
  setAuth: saveAuth,
  clearAuth: clearAuth,

  /**
   * Health check
   */
  async getHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      return await handleResponse(res);
    } catch (err) {
      console.warn("Backend health check failed:", err.message);
      return { status: "offline", error: err.message };
    }
  },

  // ==========================================
  // Authentication Endpoints
  // ==========================================

  /**
   * User Registration (default role: viewer)
   */
  async register(fullName, email, password) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        email: email,
        password: password,
      }),
    });
    const data = await handleResponse(res);
    if (data.token) {
      saveAuth(data.token, data.user, true);
    }
    return data;
  },

  /**
   * User Login
   */
  async login(email, password, remember = false) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        password: password,
        remember: Boolean(remember),
      }),
    });
    const data = await handleResponse(res);
    if (data.token) {
      saveAuth(data.token, data.user, remember);
    }
    return data;
  },

  /**
   * Retrieve profile of current authenticated user
   */
  async getMe() {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse(res);
  },

  /**
   * User Logout
   */
  async logout() {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
    } catch (err) {
      console.warn("Logout request failed:", err.message);
    } finally {
      clearAuth();
    }
  },

  /**
   * Request password reset token
   */
  async forgotPassword(email) {
    const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    return await handleResponse(res);
  },

  /**
   * Submit new password with reset token
   */
  async resetPassword(token, newPassword) {
    const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    });
    return await handleResponse(res);
  },

  // ==========================================
  // Document Management Endpoints
  // ==========================================

  /**
   * List all uploaded documents
   */
  async getDocuments() {
    const res = await fetch(`${API_BASE}/api/documents`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse(res);
  },

  /**
   * Upload a PDF or DOCX file (Requires admin or editor role)
   */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });
    return await handleResponse(res);
  },

  /**
   * Delete a document and its vectors (Requires admin or editor role)
   */
  async deleteDocument(documentId) {
    const res = await fetch(`${API_BASE}/api/documents/${documentId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    return await handleResponse(res);
  },

  /**
   * Re-index or index a document's chunks into ChromaDB
   */
  async indexDocument(documentId) {
    const res = await fetch(`${API_BASE}/api/documents/${documentId}/index`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    return await handleResponse(res);
  },

  /**
   * Retrieve chunks with page numbers for source inspection
   */
  async getDocumentChunks(documentId) {
    const res = await fetch(`${API_BASE}/api/documents/${documentId}/chunks`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse(res);
  },

  /**
   * Get safe view/download URL for a document file with attached session token
   */
  getDocumentFileUrl(documentId) {
    const token = getStoredToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : "";
    return `${API_BASE}/api/documents/${documentId}/file${query}`;
  },

  // ==========================================
  // Semantic Search & RAG Assistant
  // ==========================================

  /**
   * Ask the AI Assistant with document grounding and citations
   * Supports target language ('en', 'ta', 'hi')
   */
  async askAssistant(question, { topK = 5, documentId = null, sessionId = null, language = "en" } = {}) {
    const res = await fetch(`${API_BASE}/api/rag/ask`, {
      method: "POST",
      headers: getAuthHeaders({
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        question,
        top_k: topK,
        document_id: documentId,
        session_id: sessionId,
        language: language,
      }),
    });
    return await handleResponse(res);
  },

  /**
   * Perform semantic vector search
   */
  async semanticSearch(query, { topK = 5, documentId = null } = {}) {
    const res = await fetch(`${API_BASE}/api/search`, {
      method: "POST",
      headers: getAuthHeaders({
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        query,
        top_k: topK,
        document_id: documentId,
      }),
    });
    return await handleResponse(res);
  },
};
