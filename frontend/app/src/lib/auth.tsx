import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  ApiError,
  getApiBase,
  setAccessToken,
  fetchCurrentUser,
  updateCurrentUser,
  type AuthUserResponse,
  type LoginResponse
} from '@/lib/api';

export type AppRole = 'admin' | 'logistics_manager' | 'inventory_manager' | 'courier';

export interface AuthUser {
  id?: string;
  name: string;
  email: string;
  role: AppRole;
  courier_id?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string; role?: AppRole }>;
  googleLogin: (idToken: string, role: AppRole) => Promise<{ success: boolean; message?: string; role?: AppRole }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateProfile: (payload: { name: string }) => Promise<{ success: boolean; message?: string }>;
}

const STORAGE_KEY = 'intellisupply_user';

/* ✅ FIXED: Courier now routed correctly */
export const ROLE_HOME: Record<AppRole, string> = {
  admin: '/admin/dashboard',
  logistics_manager: '/logistics',
  inventory_manager: '/inventory',
  courier: '/courier',
};

export function normalizeRole(role: string | undefined | null): AppRole | null {
  const value = (role ?? '').trim().toLowerCase();

  if (value === 'admin' || value === 'administrator') return 'admin';
  if (value === 'courier') return 'courier';
  if (value === 'inventory_manager' || value === 'inventory') return 'inventory_manager';
  if (value === 'logistics_manager' || value === 'logistics') return 'logistics_manager';

  return null;
}

function toAuthUser(user: AuthUserResponse): AuthUser {
  const role = normalizeRole(user.role) ?? 'courier';

  return {
    id: user.id,
    name: user.name,
    email: user.email,
    role,
    courier_id: user.courier_id,
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  /* ✅ Session persistence */
  const persistSession = useCallback((nextUser: AuthUser, token?: string | null) => {
    const role = normalizeRole(nextUser.role) ?? nextUser.role;
    const normalizedUser = { ...nextUser, role };

    setUser(normalizedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizedUser));

    if (token) setAccessToken(token);
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    setAccessToken(null);
  }, []);

  /* ✅ Silent refresh (OAuth session restore) */
  const performSilentRefresh = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (res.ok) {
        const data = (await res.json()) as LoginResponse;

        if (data.success && data.user && data.access_token) {
          const authUser = toAuthUser(data.user);
          persistSession(authUser, data.access_token);
          return true;
        }
      }
    } catch (err) {
      console.error('Silent refresh failed:', err);
    }

    clearSession();
    return false;
  }, [persistSession, clearSession]);

  /* ✅ App init */
  useEffect(() => {
    let active = true;

    const initAuth = async () => {
      setLoading(true);
      await performSilentRefresh();
      if (active) setLoading(false);
    };

    initAuth();

    return () => {
      active = false;
    };
  }, [performSilentRefresh]);

  /* ✅ Auto refresh every 14 mins */
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(() => {
      performSilentRefresh();
    }, 14 * 60 * 1000);

    return () => clearInterval(interval);
  }, [user, performSilentRefresh]);

  /* ✅ LOGIN */
  const login = async (
    email: string,
    password: string,
  ): Promise<{ success: boolean; message?: string; role?: AppRole }> => {
    try {
      const res = await fetch(`${getApiBase()}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include',
      });

      const data = (await res.json()) as LoginResponse & { message?: string };

      if (res.ok && data.success && data.user && data.access_token) {
        const authUser = toAuthUser(data.user);
        persistSession(authUser, data.access_token);

        return { success: true, role: authUser.role };
      }

      return { success: false, message: data.message ?? 'Invalid credentials.' };
    } catch {
      return { success: false, message: 'Unable to reach authentication service.' };
    }
  };

  /* ✅ GOOGLE LOGIN (FIXED ROLE SUPPORT) */
  const googleLogin = async (
    idToken: string,
    role: AppRole,
  ): Promise<{ success: boolean; message?: string; role?: AppRole }> => {
    try {
      const res = await fetch(`${getApiBase()}/api/google-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id_token: idToken,
          role,
        }),
        credentials: 'include',
      });

      const data = (await res.json()) as LoginResponse & { message?: string };

      if (res.ok && data.success && data.user && data.access_token) {
        const authUser = toAuthUser(data.user);
        persistSession(authUser, data.access_token);

        return { success: true, role: authUser.role };
      }

      return { success: false, message: data.message ?? 'Google login failed.' };
    } catch {
      return { success: false, message: 'Unable to reach authentication service.' };
    }
  };

  const logout = useCallback(async () => {
    try {
      await fetch(`${getApiBase()}/api/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('Logout request failed:', err);
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await fetchCurrentUser();
      setUser(toAuthUser(userData));
    } catch {
      // ignore
    }
  }, []);

  const updateProfile = useCallback(async (payload: { name: string }) => {
    try {
      const userData = await updateCurrentUser(payload);
      setUser(toAuthUser(userData));

      return { success: true };
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Profile update failed.';
      return { success: false, message };
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, googleLogin, logout, refreshUser, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }

  return ctx;
}