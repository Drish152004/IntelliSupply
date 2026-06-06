import { Lock, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router';
import { useMemo, useState } from 'react';

const roleConfig: Record<
  string,
  { badge: string; description: string; redirect: string }
> = {
  inventory: {
    badge: 'Inventory Manager Access',
    description: 'Monitor stock health, warehouse inventory and reorder operations.',
    redirect: '/inventory',
  },
  logistics: {
    badge: 'Logistics Head Access',
    description: 'Orchestrate shipments, routes, and live dispatch operations.',
    redirect: '/logistics',
  },
  admin: {
    badge: 'Administrator Access',
    description: 'Govern platform analytics, users, and enterprise controls.',
    redirect: '/admin/dashboard',
  },
};

const defaultConfig = roleConfig.inventory;

export default function Login() {
  const navigate = useNavigate();
  const { role } = useParams<{ role?: string }>();
  const config = useMemo(
    () => (role && roleConfig[role] ? roleConfig[role] : defaultConfig),
    [role],
  );

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    navigate(config.redirect);
  };

  return (
    <div className="min-h-screen bg-[#abdbe3] grid lg:grid-cols-2">
      <section className="hidden lg:flex relative overflow-hidden bg-[#2596be] px-16 py-16">
        <div className="relative z-10 flex flex-col justify-center max-w-2xl">
          <div className="inline-flex w-fit items-center rounded-full bg-white px-6 py-3 shadow-sm">
            <span className="text-2xl font-semibold text-slate-950">
              Intelli<span className="text-sky-600">Supply</span>
            </span>
          </div>

          <div className="mt-20">
            <p className="text-sm uppercase tracking-[0.35em] text-white">
              Enterprise operations platform
            </p>

            <h1 className="mt-8 text-7xl font-semibold leading-[0.95] tracking-tight text-white">
              Intelligent control across inventory and logistics
            </h1>

            <p className="mt-10 text-2xl leading-10 text-slate-300">
              Unified operational visibility for warehouse intelligence,
              shipment orchestration, fulfilment optimization and enterprise
              governance.
            </p>
          </div>
        </div>

        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.12),transparent_30%)]" />
      </section>

      <section className="flex items-center justify-center px-6 py-10">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="w-full max-w-[620px] rounded-[3rem] border border-slate-200 bg-white p-10 lg:p-14 shadow-sm"
        >
          <div className="inline-flex items-center rounded-full bg-sky-50 px-5 py-3">
            <span className="text-base font-semibold text-sky-900">{config.badge}</span>
          </div>

          <h2 className="mt-10 text-6xl font-semibold tracking-tight text-slate-950">
            Welcome back
          </h2>

          <p className="mt-6 text-xl leading-9 text-slate-500">{config.description}</p>

          <form className="mt-12 space-y-8" onSubmit={handleSubmit}>
            <div>
              <label className="mb-4 block text-base font-semibold text-slate-900">
                Email address
              </label>

              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@intellisupply.ai"
                className="h-16 w-full rounded-3xl border border-slate-200 bg-slate-50 px-6 text-lg outline-none transition focus:border-slate-400"
              />
            </div>

            <div>
              <div className="mb-4 flex items-center justify-between">
                <label className="text-base font-semibold text-slate-900">Password</label>

                <button
                  type="button"
                  className="text-base text-slate-500 hover:text-slate-900"
                >
                  Forgot password
                </button>
              </div>

              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="h-16 w-full rounded-3xl border border-slate-200 bg-slate-50 px-6 text-lg outline-none transition focus:border-slate-400"
              />
            </div>

            <div className="flex items-center gap-4 rounded-3xl bg-slate-50 px-6 py-5">
              <Lock className="h-5 w-5 text-slate-600" />
              <span className="text-base text-slate-700">Secure enterprise authentication</span>
            </div>

            <button
              type="submit"
              className="flex h-16 w-full items-center justify-center gap-3 rounded-full bg-slate-950 text-lg font-semibold text-white transition-all hover:scale-[1.01]"
            >
              Sign in
              <ArrowRight className="h-5 w-5" />
            </button>
          </form>

          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-10 w-full text-center text-base text-slate-500 hover:text-slate-900"
          >
            Return to landing page
          </button>
        </motion.div>
      </section>
    </div>
  );
}
