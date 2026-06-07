import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { ApiError, getApiBase, setAccessToken, type AuthUserResponse, type LoginResponse } from '@/lib/api';

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
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateProfile: (payload: { name: string }) => Promise<{ success: boolean; message?: string }>;
}

const DEMO_ENABLED = import.meta.env.VITE_DEMO_AUTH !== 'false';

const DEMO_USERS: Record<string, { password: string; user: AuthUser }> = {
  'admin@demo.com': {
    password: 'admin',
    user: { id: 'demo-admin', name: 'Admin Demo', email: 'admin@demo.com', role: 'admin' },
  },
  'logistics@demo.com': {
    password: 'logistics',
    user: { id: 'demo-logistics', name: 'Logistics Demo', email: 'logistics@demo.com', role: 'logistics_manager' },
  },
  'inventory@demo.com': {
    password: 'inventory',
    user: { id: 'demo-inventory', name: 'Inventory Demo', email: 'inventory@demo.com', role: 'inventory_manager' },
  },
};

const STORAGE_KEY = 'intellisupply_user';

export const ROLE_HOME: Record<AppRole, string> = {
  admin: '/admin/dashboard',
  logistics_manager: '/logistics',
  inventory_manager: '/inventory',
  courier: '/logistics',
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

  const persistSession = useCallback((nextUser: AuthUser, token?: string | null) => {
    const role = normalizeRole(nextUser.role) ?? nextUser.role;
    const normalizedUser = { ...nextUser, role };
    setUser(normalizedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizedUser));
    if (token) {
      setAccessToken(token);
    }
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    setAccessToken(null);
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as AuthUser;
        const role = normalizeRole(parsed.role);
        if (role) {
          setUser({ ...parsed, role });
        } else {
          clearSession();
        }
      }
    } catch {
      clearSession();
    } finally {
      setLoading(false);
    }
  }, [clearSession]);

  const login = async (
    email: string,
    password: string,
  ): Promise<{ success: boolean; message?: string; role?: AppRole }> => {
    try {
      const res = await fetch(`${getApiBase()}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(5000),
      });
      const data = (await res.json()) as LoginResponse & { message?: string };
      if (res.ok && data.success && data.user && data.access_token) {
        const authUser = toAuthUser(data.user);
        persistSession(authUser, data.access_token);
        return { success: true, role: authUser.role };
      }
      return { success: false, message: data.message ?? 'Invalid credentials.' };
    } catch {
      if (!DEMO_ENABLED) {
        return { success: false, message: 'Unable to reach authentication service.' };
      }
    }

    if (DEMO_ENABLED) {
      const entry = DEMO_USERS[email.toLowerCase().trim()];
      if (entry && entry.password === password) {
        persistSession(entry.user, null);
        return { success: true, role: entry.user.role };
      }
    }

    return {
      success: false,
      message: 'Invalid credentials. Try demo: admin@demo.com / admin',
    };
  };

  const logout = () => {
    clearSession();
  };

  const refreshUser = async () => {
    const token = localStorage.getItem('intellisupply_token');
    if (!token) return;
    try {
      const res = await fetch(`${getApiBase()}/api/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = (await res.json()) as { user: AuthUserResponse };
      persistSession(toAuthUser(data.user), token);
    } catch {
      // ignore refresh errors
    }
  };

  const updateProfile = async (payload: { name: string }) => {
    try {
      const token = localStorage.getItem('intellisupply_token');
      if (!token) {
        return { success: false, message: 'Not authenticated.' };
      }
      const res = await fetch(`${getApiBase()}/api/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        return { success: false, message: data.message ?? 'Profile update failed.' };
      }
      persistSession(toAuthUser(data.user), token);
      return { success: true };
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Profile update failed.';
      return { success: false, message };
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
