/**
 * src/services/auth.api.ts
 *
 * API calls for Authentication endpoints.
 * POST /api/auth/login   — OAuth2 form-encoded (username + password)
 * POST /api/auth/register
 * GET  /api/auth/me
 */

import api from './api';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

/** Login — backend expects OAuth2 form data (username = email). */
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const form = new URLSearchParams();
  form.append('username', payload.email);
  form.append('password', payload.password);

  const { data } = await api.post<TokenResponse>('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

/** Register a new user. */
export async function register(payload: RegisterPayload): Promise<UserProfile> {
  const { data } = await api.post<UserProfile>('/api/auth/register', payload);
  return data;
}

/** Get the currently authenticated user. */
export async function getProfile(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>('/api/auth/me');
  return data;
}
