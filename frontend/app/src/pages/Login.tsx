import { Lock, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router';
import { useMemo, useState } from 'react';
import { useAuth, ROLE_HOME } from '@/lib/auth';

const roleConfig: Record<
  string,
  { badge: string; description: string }
> = {
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
};

const defaultConfig = roleConfig.inventory;

export default function Login() {
  const navigate = useNavigate();
  const { role } = useParams<{ role?: string }>();
  const { login } = useAuth();

  const config = useMemo(
    () => (role && roleConfig[role] ? roleConfig[role] : defaultConfig),
    [role],
  );

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // Redirect to the role's home page
      navigate(ROLE_HOME[result.role!], { replace: true });
    } catch {
      setError('Unexpected error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#abdbe3] grid lg:grid-cols-2">
      {/* Left panel */}
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

            <h1 className="mt-6 text-4xl font-semibold leading-[1.1] tracking-tight text-white sm:text-5xl">
              Intelligent control across inventory and logistics
            </h1>

            <p className="mt-8 text-lg leading-8 text-slate-200">
              Unified operational visibility for warehouse intelligence,
              shipment orchestration, fulfilment optimization and enterprise
              governance.
            </p>
          </div>
        </div>

        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.12),transparent_30%)]" />
      </section>

      {/* Right panel — form */}
      <section className="flex items-center justify-center px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-[520px] rounded-[2.5rem] border border-slate-200 bg-white p-7 lg:p-10 shadow-sm"
        >
          <div className="inline-flex items-center rounded-full bg-sky-50 px-4 py-2">
            <span className="text-sm font-semibold text-sky-900">{config.badge}</span>
          </div>

          <h2 className="mt-7 text-3xl font-semibold tracking-tight text-slate-950">
            Welcome back
          </h2>

          <p className="mt-3 text-base leading-7 text-slate-500">{config.description}</p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@intellisupply.ai"
                required
                className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-5 text-base outline-none transition focus:border-slate-400"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-semibold text-slate-900">Password</label>
                <button type="button" className="text-sm text-slate-500 hover:text-slate-900">
                  Forgot password
                </button>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-5 text-base outline-none transition focus:border-slate-400"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-5 py-4">
              <Lock className="h-4 w-4 text-slate-600" />
              <span className="text-sm text-slate-700">Secure enterprise authentication</span>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="flex h-12 w-full items-center justify-center gap-3 rounded-full bg-slate-950 text-base font-semibold text-white transition-all hover:scale-[1.01] disabled:opacity-60"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 rounded-2xl bg-slate-50 px-4 py-3">
            <p className="text-xs text-slate-500 font-medium">Demo credentials</p>
            <div className="mt-1.5 space-y-0.5 text-xs text-slate-400">
              <p>admin@demo.com / admin</p>
              <p>logistics@demo.com / logistics</p>
              <p>inventory@demo.com / inventory</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-6 w-full text-center text-sm text-slate-500 hover:text-slate-900"
          >
            Return to landing page
          </button>
        </motion.div>
      </section>
    </div>
  );
}
