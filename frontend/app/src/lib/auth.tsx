import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AppRole = 'admin' | 'logistics_manager' | 'inventory_manager';

export interface AuthUser {
  id?: string;
  name: string;
  email: string;
  role: AppRole;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string; role?: AppRole }>;
  logout: () => void;
}

// ─── Demo fallback credentials (used when backend is unreachable) ─────────────

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

// ─── Role redirect map ────────────────────────────────────────────────────────

export const ROLE_HOME: Record<AppRole, string> = {
  admin: '/admin/dashboard',
  logistics_manager: '/logistics',
  inventory_manager: '/inventory',
};

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw));
    } catch {
      // ignore corrupt storage
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (
    email: string,
    password: string,
  ): Promise<{ success: boolean; message?: string; role?: AppRole }> => {
    // 1. Try real backend
    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(5000),
      });
      const data = await res.json();
      if (res.ok && data.success && data.user) {
        const authUser: AuthUser = {
          id: data.user.id,
          name: data.user.name,
          email: data.user.email,
          role: data.user.role as AppRole,
        };
        setUser(authUser);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
        return { success: true, role: authUser.role };
      }
      // Backend reachable but auth failed
      return { success: false, message: data.message ?? 'Invalid credentials.' };
    } catch {
      // Backend unreachable — fall through to demo credentials
    }

    // 2. Demo credential fallback
    const entry = DEMO_USERS[email.toLowerCase().trim()];
    if (entry && entry.password === password) {
      setUser(entry.user);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(entry.user));
      return { success: true, role: entry.user.role };
    }

    return {
      success: false,
      message: 'Invalid credentials. Try demo: admin@demo.com / admin',
    };
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
