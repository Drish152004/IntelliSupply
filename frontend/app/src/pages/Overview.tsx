import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Package, Truck, TrendingUp, ShieldCheck, Users } from 'lucide-react';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { getDashboardSummary, listHubLocations, type DashboardSummary, type HubMapLocation } from '@/lib/api';

const defaultSummary: DashboardSummary = {
  sales_volume_label: 'This week',
  sales_volume_value: '—',
  logistics_reliability_pct: 92.4,
  hardware_uptime_pct: 98.7,
  active_sessions: 0,
  orders_funnel: 0,
  route_on_time_pct: 87,
  recent_shipments: 0,
};

export default function Overview() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(defaultSummary);
  const [hubLocations, setHubLocations] = useState<HubMapLocation[]>([]);

  useEffect(() => {
    void getDashboardSummary()
      .then(setSummary)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    void listHubLocations()
      .then(setHubLocations)
      .catch(() => setHubLocations([]));
  }, []);

  const summaryCards = [
    {
      label: 'Sales volume',
      value: summary.sales_volume_value,
      detail: summary.sales_volume_label,
      color: 'border-pink-100 bg-pink-50 text-pink-900',
      icon: TrendingUp,
    },
    {
      label: 'Logistics reliability',
      value: `${summary.logistics_reliability_pct}%`,
      detail: 'On-time routes',
      color: 'border-sky-100 bg-sky-50 text-sky-900',
      icon: Truck,
    },
    {
      label: 'Hardware uptime',
      value: `${summary.hardware_uptime_pct}%`,
      detail: 'Hub devices',
      color: 'border-emerald-100 bg-emerald-50 text-emerald-900',
      icon: ShieldCheck,
    },
    {
      label: 'User sessions',
      value: summary.active_sessions.toLocaleString(),
      detail: 'Derived from recent shipments',
      color: 'border-amber-100 bg-amber-50 text-amber-900',
      icon: Users,
    },
  ];

  const salesCards = [
    {
      title: 'Orders funnel',
      subtitle: 'Sales and logistics aligned in one view',
      value: `${summary.orders_funnel} new`,
      icon: Package,
    },
    {
      title: 'Route pulse',
      subtitle: 'Live dispatch and transit health',
      value: `${summary.route_on_time_pct}% on time`,
      icon: Truck,
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <p className="text-sm uppercase tracking-[0.32em] text-muted-foreground mb-2"></p>
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-foreground">Admin Overview</h1>
          <p className="max-w-3xl mt-4 text-sm leading-7 text-muted-foreground">
            One centralized view for commerce performance, delivery operations, and user engagement metrics.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid gap-6 md:grid-cols-2 xl:grid-cols-4 mb-10">
          {summaryCards.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.label} className={`rounded-[1.75rem] border p-6 shadow-sm ${card.color}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] font-semibold">{card.label}</p>
                    <h2 className="mt-4 text-3xl font-semibold">{card.value}</h2>
                  </div>
                  <div className="rounded-3xl bg-white/80 p-3 shadow-sm">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
                <p className="mt-5 text-sm text-current/80">{card.detail}</p>
              </div>
            );
          })}
        </motion.div>

        <div className="grid gap-6 xl:grid-cols-[1.6fr_0.95fr]">
          <section className="space-y-6">
            {/* <div className="page-card">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Admin Copilot</p>
                  <h2 className="text-2xl font-semibold text-foreground">AI guidance for approvals and operations</h2>
                </div>
                <button className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm">
                  Launch Copilot
                </button>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                Ask the admin copilot for system health, user metrics, and logistics guidance right from the dashboard.
              </p>
            </div> */}

            <div className="page-card">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Sales & logistics</p>
                  <h2 className="text-2xl font-semibold text-foreground">Revenue and delivery flow</h2>
                </div>
                <button
                  onClick={() => navigate('/inventory')}
                  className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm"
                >
                  Open inventory
                </button>
              </div>
              <div className="grid gap-4 md:grid-cols-2 mt-6">
                {salesCards.map((card) => {
                  const Icon = card.icon;
                  return (
                    <div key={card.title} className="rounded-[1.75rem] border border-border bg-white p-5 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.22em] font-semibold text-muted-foreground">{card.title}</p>
                          <p className="mt-3 text-base text-muted-foreground">{card.subtitle}</p>
                        </div>
                        <Icon className="w-5 h-5 text-slate-700" />
                      </div>
                      <p className="mt-6 text-3xl font-semibold text-foreground">{card.value}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="page-card">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Live route preview</p>
                  <h2 className="text-2xl font-semibold text-foreground">Active delivery coverage</h2>
                </div>
                <button
                  onClick={() => navigate('/routes')}
                  className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm"
                >
                  View logistics
                </button>
              </div>
              <div className="mt-6 h-[520px] overflow-hidden rounded-[1.75rem] border border-slate-200">
                <RouteMap hubLocations={hubLocations} chinaMapOnly />
              </div>
            </div>
          </section>

          <aside className="page-card flex min-h-[680px] flex-col overflow-hidden">
            <div className="border-b border-border p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">AI copilot</p>
              <h2 className="mt-3 text-3xl font-semibold text-foreground">Admin assistant</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Ask the admin copilot to summarize health, plan approvals, or check logistics performance.
              </p>
            </div>
            <div className="mt-5 flex-1 overflow-hidden">
              <AICopilot />
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
