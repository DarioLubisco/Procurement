import { useState, useCallback, useEffect, createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import type { AuthUser, AuthState, LoginCredentials } from '@/types/auth';

// ─── Storage keys ────────────────────────────────────────────────────────────
const TOKEN_KEY = 'synapse_token';
const USER_KEY = 'synapse_user';

// ─── Context ─────────────────────────────────────────────────────────────────
interface AuthContextValue extends AuthState {
  login: (creds: LoginCredentials) => Promise<void>;
  logout: () => void;
  can: (module: string, write?: boolean) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Provider ────────────────────────────────────────────────────────────────
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<AuthState>(() => {
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const raw = localStorage.getItem(USER_KEY);
      if (token && raw) {
        const user: AuthUser = JSON.parse(raw);
        // Quick expiry check via jose-less base64 decode
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 > Date.now()) {
          return { user, token, isAuthenticated: true, isLoading: false };
        }
      }
    } catch {
      // ignore parse errors
    }
    return { user: null, token: null, isAuthenticated: false, isLoading: false };
  });

  // Clear expired token on mount
  useEffect(() => {
    if (!state.isAuthenticated) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }, [state.isAuthenticated]);

  const login = useCallback(async (creds: LoginCredentials) => {
    setState(s => ({ ...s, isLoading: true }));
    try {
      const res = await fetch(
        `/api/auth/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(creds),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? 'Credenciales incorrectas');
      }
      const data = await res.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      setState({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      setState(s => ({ ...s, isLoading: false }));
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
  }, []);

  const can = useCallback(
    (module: string, write = false): boolean => {
      if (!state.user) return false;
      const perm = state.user.permissions[module];
      if (!perm) return false;
      return write ? perm.w : perm.r;
    },
    [state.user]
  );

  return (
    <AuthContext.Provider value={{ ...state, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
};

// ─── Hook ─────────────────────────────────────────────────────────────────────
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
};

// ─── Helper: get token for API calls ─────────────────────────────────────────
export const getAuthToken = (): string | null => localStorage.getItem(TOKEN_KEY);
