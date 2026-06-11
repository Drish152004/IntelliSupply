import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router';
import { useMemo, useState, useEffect, useRef } from 'react';
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
  const { login, googleLogin } = useAuth();

  const config = useMemo(
    () => (role && roleConfig[role] ? roleConfig[role] : defaultConfig),
    [role],
  );

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  //  Google button ref
  const googleButtonRef = useRef<HTMLDivElement | null>(null);

  //  Google init (NON-INTRUSIVE)
  useEffect(() => {
    if (!window.google || !googleButtonRef.current) return;

    window.google.accounts.id.initialize({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      callback: async (response: any) => {
        setSubmitting(true);
        setError(null);

        try {
          const result = await googleLogin(response.credential);

          if (result.success) {
            const role = result.role;
            const home = role ? ROLE_HOME[role] : '/';
            navigate(home ?? '/', { replace: true });
          } else {
            setError(result.message ?? 'Google login failed');
          }
        } catch {
          setError('Google login failed. Please try again.');
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
        shape: 'pill',
      }
    );
  }, [navigate]);

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
      const home = result.role ? ROLE_HOME[result.role] : '/';
      navigate(home ?? '/', { replace: true });
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
            {/* EMAIL */}
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
                className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-5"
              />
            </div>

            {/* PASSWORD */}
            <div>
              <label className="text-sm font-semibold text-slate-900">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-5 mt-2"
              />
            </div>

            {/* ERROR */}
            {error && (
              <div className="text-red-600 text-sm">{error}</div>
            )}

            {/* BUTTON */}
            <button
              type="submit"
              disabled={submitting}
              className="flex h-12 w-full items-center justify-center gap-3 rounded-full bg-slate-950 text-white"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Sign in'}
            </button>
          </form>

          {/*  Google Divider */}
          <div className="mt-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-slate-200" />
            <span className="text-xs text-slate-400">OR</span>
            <div className="h-px flex-1 bg-slate-200" />
          </div>

          {/*  Google Button */}
          <div ref={googleButtonRef} className="mt-4 flex justify-center" />

          {/*  Demo */}
          <div className="mt-6 text-xs text-slate-400">
            admin@demo.com / admin
          </div>

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
