/**
 * src/context/AuthContext.tsx
 *
 * Provides authentication state (user, token) and actions (login, logout, register)
 * to the entire app via React context.
 *
 * Token is persisted to localStorage under the key `prepai_token`.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { TOKEN_KEY } from '../services/api';
import * as authApi from '../services/auth.api';
import type { UserProfile } from '../services/auth.api';

// ── Context shape ──────────────────────────────────────────────────────

interface AuthContextValue {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ───────────────────────────────────────────────────────────

export function AuthProvider({ children, onUnauthorized }: {
  children: ReactNode;
  onUnauthorized?: () => void;
}) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [isLoading, setIsLoading] = useState(!!localStorage.getItem(TOKEN_KEY));

  /** Persist token and load profile on mount if token exists. */
  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    authApi.getProfile()
      .then((profile) => setUser(profile))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  /** Listen for 401 events fired by the Axios interceptor. */
  useEffect(() => {
    const handler = () => {
      setToken(null);
      setUser(null);
      onUnauthorized?.();
    };
    window.addEventListener('prepai:unauthorized', handler);
    return () => window.removeEventListener('prepai:unauthorized', handler);
  }, [onUnauthorized]);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login({ email, password });
    localStorage.setItem(TOKEN_KEY, access_token);
    setToken(access_token);
    // profile will be loaded by the useEffect above
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    await authApi.register({ name, email, password });
    // Auto-login after registration
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    onUnauthorized?.();
  }, [onUnauthorized]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
