import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, ShieldCheck, BarChart as BarIcon, Activity, Users } from 'lucide-react';
import { getDashboardSummary, listUsers } from '@/lib/api';

export default function AdminAnalytics() {
  const [summary, setSummary] = useState<{ recent_shipments: number; logistics_reliability_pct: number } | null>(null);
  const [userCount, setUserCount] = useState(0);

  useEffect(() => {
    void getDashboardSummary()
      .then((data) => setSummary({ recent_shipments: data.recent_shipments, logistics_reliability_pct: data.logistics_reliability_pct }))
      .catch(() => undefined);
    void listUsers()
      .then((users) => setUserCount(users.length))
      .catch(() => undefined);
  }, []);

  const kpis = [
    { label: 'Recent shipments', value: String(summary?.recent_shipments ?? '—'), detail: 'Neo4j orders' },
    { label: 'Logistics reliability', value: `${summary?.logistics_reliability_pct ?? '—'}%`, detail: 'Derived metric' },
    { label: 'Directory accounts', value: String(userCount || '—'), detail: 'Profiles + couriers' },
    { label: 'Data access reviews', value: '14 due', detail: 'This week' },
  ];

  const incidentSeries = [
    { month: 'Jan', incidents: 46, mitigated: 33 },
    { month: 'Feb', incidents: 41, mitigated: 35 },
    { month: 'Mar', incidents: 38, mitigated: 36 },
    { month: 'Apr', incidents: 34, mitigated: 33 },
    { month: 'May', incidents: 30, mitigated: 29 },
    { month: 'Jun', incidents: 28, mitigated: 27 },
  ];

  const trafficSeries = [
    { month: 'Jan', review: 520, escalation: 110 },
    { month: 'Feb', review: 540, escalation: 103 },
    { month: 'Mar', review: 560, escalation: 98 },
    { month: 'Apr', review: 590, escalation: 86 },
    { month: 'May', review: 610, escalation: 72 },
    { month: 'Jun', review: 640, escalation: 61 },
  ];

  const roleDistribution = [
    { name: 'Admin', value: 22 },
    { name: 'Ops', value: 34 },
    { name: 'Analyst', value: 18 },
    { name: 'Support', value: 26 },
  ];

  const pieColors = ['#0f172a', '#0369a1', '#16a34a', '#f59e0b'];

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
                Track compliance, admin activity, and permission trends with operational clarity.
              </p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-900">
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

        <section className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr] mb-8">
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4 mb-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Incident volume vs. mitigations</p>
                <p className="text-xs text-muted-foreground">Monitoring reduction in issue backlog.</p>
              </div>
              <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700">Operational
                trending</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={incidentSeries} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="month" tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 16, borderColor: 'var(--border)', boxShadow: '0 12px 30px rgba(15,23,42,0.08)' }} />
                  <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '12px', paddingBottom: '8px' }} />
                  <Line type="monotone" dataKey="incidents" stroke="#ef4444" strokeWidth={3} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="mitigated" stroke="#0f172a" strokeWidth={3} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <p className="text-sm font-semibold text-foreground">Review traffic</p>
                  <p className="text-xs text-muted-foreground">Admin review volume compared to escalations.</p>
                </div>
                <Activity className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trafficSeries} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: 16, borderColor: 'var(--border)', boxShadow: '0 12px 30px rgba(15,23,42,0.08)' }} />
                    <Bar dataKey="review" stackId="a" fill="#0f172a" radius={[10, 10, 0, 0]} />
                    <Bar dataKey="escalation" stackId="a" fill="#f59e0b" radius={[10, 10, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4 mb-5">
                <div>
                  <p className="text-sm font-semibold text-foreground">Role distribution</p>
                  <p className="text-xs text-muted-foreground">Access distribution across admin functions.</p>
                </div>
                <ShieldCheck className="h-5 w-5 text-sky-600" />
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={roleDistribution} dataKey="value" nameKey="name" innerRadius={46} outerRadius={76} paddingAngle={4}>
                      {roleDistribution.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={pieColors[index]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-3 mt-4 text-xs text-muted-foreground">
                  {roleDistribution.map((entry) => (
                    <div key={entry.name} className="rounded-2xl bg-slate-50 p-3">
                      <p className="font-semibold text-foreground">{entry.name}</p>
                      <p>{entry.value}%</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-sm font-semibold text-foreground">Efficiency forecast</p>
                <p className="text-xs text-muted-foreground">Projected reduction in manual review hours.</p>
              </div>
            </div>
            <p className="text-3xl font-semibold text-black">+12%</p>
            <p className="mt-3 text-sm text-muted-foreground">Automated policy enforcement is expected to reduce overhead next quarter.</p>
          </div>

          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Users className="h-5 w-5 text-sky-600" />
              <div>
                <p className="text-sm font-semibold text-foreground">User adoption</p>
                <p className="text-xs text-muted-foreground">Role-based workflows adopted by leaders.</p>
              </div>
            </div>
            <p className="text-3xl font-semibold text-black">89%</p>
            <p className="mt-3 text-sm text-muted-foreground">Users actively engaging with admin controls across active regions.</p>
          </div>

          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-sm font-semibold text-foreground">Policy gaps</p>
                <p className="text-xs text-muted-foreground">Pending compliance checks to close.</p>
              </div>
            </div>
            <p className="text-3xl font-semibold text-black">3</p>
            <p className="mt-3 text-sm text-muted-foreground">High-risk policies are under active review by security operations.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
