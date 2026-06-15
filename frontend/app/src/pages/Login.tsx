import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router';
import { useMemo, useState, useEffect, useRef } from 'react';
import { useAuth, ROLE_HOME, type AppRole } from '@/lib/auth';

const roleConfig: Record<string, { badge: string; description: string }> = {
  inventory: {
    badge: 'Inventory Manager Access',
    description: 'Monitor stock health, warehouse inventory and reorder operations.',
  },
  logistics: {
    badge: 'Logistics Head Access',
    description: 'Orchestrate shipments, routes, and live dispatch operations.',
  },
  admin: {
    badge: 'Administrator Access',
    description: 'Govern platform analytics, users, and enterprise controls.',
  },
  courier: {
    badge: 'Courier Access',
    description: 'View deliveries, assigned shipments and route details.',
  },
};

const ROLE_MAP: Record<string, AppRole> = {
  admin: 'admin',
  logistics: 'logistics_manager',
  inventory: 'inventory_manager',
  courier: 'courier',
};

const defaultConfig = roleConfig.inventory;

export default function Login() {
  const navigate = useNavigate();
  const { role } = useParams<{ role?: string }>();
  const { login, googleLogin } = useAuth();

  const config = useMemo(
    () => (role && roleConfig[role] ? roleConfig[role] : defaultConfig),
    [role],
  );

  // ✅ Resolve selected role (important for Google login)
  const selectedRole: AppRole = ROLE_MAP[role ?? 'courier'] || 'courier';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const googleButtonRef = useRef<HTMLDivElement | null>(null);

  /* ✅ GOOGLE LOGIN (FIXED WITH ROLE) */
useEffect(() => {
  if (!window.google || !googleButtonRef.current) return;

  // ✅ Prevent multiple init
  if ((window as any)._googleInitialized) return;
  (window as any)._googleInitialized = true;

  window.google.accounts.id.initialize({
    client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
    callback: async (response: any) => {
      setSubmitting(true);
      setError(null);

      try {
        const result = await googleLogin(response.credential, selectedRole);

        if (result.success && result.role) {
          navigate(ROLE_HOME[result.role], { replace: true });
        } else {
          setError(result.message ?? 'Google login failed');
        }
      } catch {
        setError('Google login failed.');
      } finally {
        setSubmitting(false);
      }
    },
  });

  window.google.accounts.id.renderButton(
    googleButtonRef.current,
    {
      theme: 'outline',
      size: 'large',
      width: 360,
    }
  );
}, [selectedRole]);
  /* ✅ NORMAL LOGIN */
  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const result = await login(email, password);

      if (!result.success) {
        setError(result.message ?? 'Login failed. Please try again.');
        return;
      }

      if (result.role) {
        navigate(ROLE_HOME[result.role], { replace: true });
      }
    } catch {
      setError('Unexpected error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#abdbe3] grid lg:grid-cols-2">
      {/* LEFT PANEL */}
      <section className="hidden lg:flex relative overflow-hidden bg-[#2596be] px-10 py-10">
        <div className="relative z-10 flex flex-col justify-center max-w-2xl">
          <div className="inline-flex w-fit items-center rounded-full bg-white px-5 py-2.5 shadow-sm">
            <span className="text-xl font-semibold text-slate-950">
              Intelli<span className="text-sky-600">Supply</span>
            </span>
          </div>

          <div className="mt-12">
            <p className="text-sm uppercase tracking-[0.35em] text-white">
              Enterprise operations platform
            </p>

            <h1 className="mt-6 text-4xl font-semibold text-white sm:text-5xl">
              Intelligent control across inventory and logistics
            </h1>

            <p className="mt-8 text-lg text-slate-200">
              Unified operational visibility for warehouse intelligence,
              shipment orchestration, fulfilment optimization and enterprise
              governance.
            </p>
          </div>
        </div>
      </section>

      {/* RIGHT PANEL */}
      <section className="flex items-center justify-center px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-[520px] rounded-[2.5rem] border border-slate-200 bg-white p-7 lg:p-10 shadow-sm"
        >
          <div className="inline-flex items-center rounded-full bg-sky-50 px-4 py-2">
            <span className="text-sm font-semibold text-sky-900">
              {config.badge}
            </span>
          </div>

          <h2 className="mt-7 text-3xl font-semibold text-slate-950">
            Welcome back
          </h2>

          <p className="mt-3 text-base text-slate-500">
            {config.description}
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@intellisupply.ai"
              required
              className="h-12 w-full rounded-2xl border bg-slate-50 px-5"
            />

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              className="h-12 w-full rounded-2xl border bg-slate-50 px-5"
            />

            {error && <div className="text-red-600 text-sm">{error}</div>}

            <button
              type="submit"
              disabled={submitting}
              className="flex h-12 w-full items-center justify-center rounded-full bg-slate-950 text-white"
            >
              {submitting ? <Loader2 className="animate-spin h-4 w-4" /> : 'Sign in'}
            </button>
          </form>

          {/* GOOGLE */}
          <div className="mt-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-slate-200" />
            <span className="text-xs text-slate-400">OR</span>
            <div className="h-px flex-1 bg-slate-200" />
          </div>

          <div ref={googleButtonRef} className="mt-4 flex justify-center" />

          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-6 w-full text-sm text-slate-500"
          >
            Return to landing page
          </button>
        </motion.div>
      </section>
    </div>
  );
}