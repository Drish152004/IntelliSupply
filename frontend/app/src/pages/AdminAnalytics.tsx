import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { ShieldCheck, BarChart as BarIcon, Users, Truck, Package } from 'lucide-react';
import { getDashboardSummary, type DashboardSummary } from '@/lib/api';

const pieColors = ['#0f172a', '#0369a1', '#16a34a', '#f59e0b', '#8b5cf6', '#ec4899'];

export default function AdminAnalytics() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    void getDashboardSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }, []);

  const loaded = summary !== null;

  const kpis = [
    {
      label: 'Recent shipments',
      value: loaded ? String(summary.recent_shipments) : '—',
      detail: 'Orders',
    },
    {
      label: 'Courier assignment',
      value: loaded ? `${summary.courier_assignment_pct}%` : '—',
      detail: 'Shipments with an assigned courier',
    },
    {
      label: 'Directory accounts',
      value: loaded ? String(summary.total_accounts) : '—',
      detail: 'Profiles and courier accounts',
    },
    {
      label: 'At-risk shipments',
      value: loaded ? String(summary.logistics.at_risk_shipments) : '—',
      detail: `Unassigned or due within the hour (${summary?.logistics.delivery_day ?? '—'})`,
    },
  ];

  const roleDistribution = useMemo(
    () =>
      (summary?.role_distribution ?? []).map((entry) => ({
        name: entry.role,
        value: entry.count,
      })),
    [summary],
  );

  const secondaryTiles = [
    {
      label: 'Active couriers',
      value: loaded ? String(summary.active_couriers) : '—',
      detail: 'All active courier accounts',
      icon: Truck,
    },
    {
      label: 'Unassigned shipments',
      value: loaded ? String(summary.unassigned_shipments) : '—',
      detail: 'Need courier assignment',
      icon: Package,
    },
    {
      label: 'Hub coverage',
      value: loaded ? String(summary.hub_count) : '—',
      detail: 'Distinct hubs in recent lanes',
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section className="mb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Admin analytics</p>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Governance intelligence</h1>
              <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
                Track operational health, account distribution, and logistics readiness from live data.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                void getDashboardSummary()
                  .then(setSummary)
                  .catch(() => setSummary(null));
              }}
              className="inline-flex items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-900"
            >
              <BarIcon className="h-4 w-4" /> Refresh metrics
            </button>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-4 mb-8">
          {kpis.map((metric) => (
            <div key={metric.label} className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">{metric.label}</p>
              <h2 className="mt-4 text-3xl font-semibold text-foreground">{metric.value}</h2>
              <p className="mt-3 text-sm text-muted-foreground">{metric.detail}</p>
            </div>
          ))}
        </section>

        {roleDistribution.length > 0 && (
          <section className="grid gap-6 xl:grid-cols-[1fr_1fr] mb-8">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <p className="text-sm font-semibold text-foreground">Role distribution</p>
                  <p className="text-xs text-muted-foreground">Accounts by role across the directory.</p>
                </div>
                <Users className="h-5 w-5 text-sky-600" />
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={roleDistribution}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={46}
                      outerRadius={76}
                      paddingAngle={4}
                    >
                      {roleDistribution.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-4 text-xs text-muted-foreground">
                {roleDistribution.map((entry) => (
                  <div key={entry.name} className="rounded-2xl bg-slate-50 p-3">
                    <p className="font-semibold text-foreground">{entry.name}</p>
                    <p>{entry.value} account{entry.value === 1 ? '' : 's'}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <p className="text-sm font-semibold text-foreground">Operational callouts</p>
                  <p className="text-xs text-muted-foreground">
                    Alerts for {summary?.logistics.delivery_day ?? 'the selected day'}.
                  </p>
                </div>
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="space-y-3">
                {(summary?.logistics.callouts ?? []).map((callout) => (
                  <div
                    key={callout.title}
                    className="rounded-2xl border border-border bg-slate-50 p-4 text-sm"
                  >
                    <p className="font-semibold text-foreground">{callout.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{callout.detail}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {secondaryTiles.map((tile) => {
            const Icon = tile.icon;
            return (
              <div key={tile.label} className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <Icon className="h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-semibold text-foreground">{tile.label}</p>
                    <p className="text-xs text-muted-foreground">{tile.detail}</p>
                  </div>
                </div>
                <p className="text-3xl font-semibold text-black">{tile.value}</p>
              </div>
            );
          })}
        </section>
      </main>
    </div>
  );
}
