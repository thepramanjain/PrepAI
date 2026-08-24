/**
 * src/services/api.ts
 *
 * Axios instance with base URL, JWT interceptor, and 401 handler.
 */

import axios from 'axios';

const TOKEN_KEY = 'prepai_token';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 ──────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      // Dispatch a custom event so AuthContext can react
      window.dispatchEvent(new Event('prepai:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export { TOKEN_KEY };
export default api;
