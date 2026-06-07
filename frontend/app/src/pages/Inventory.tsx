import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import AICopilot from '@/components/AICopilot';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, RefreshCcw, Box, ShieldCheck } from 'lucide-react';
import { getInventoryForecastTrend, getInventorySummary, listInventoryProducts } from '@/lib/api';

const fallbackMetrics = [
  { label: 'On-hand units', value: '—', detail: 'Loading...' },
  { label: 'Stockout risk', value: '—', detail: 'Loading...' },
  { label: 'Demand coverage', value: '—', detail: 'Loading...' },
  { label: 'Reorder alerts', value: '—', detail: 'Loading...' },
];

export default function Inventory() {
  const [search, setSearch] = useState('');
  const [activeStatus, setActiveStatus] = useState('All');
  const [metrics, setMetrics] = useState(fallbackMetrics);
  const [products, setProducts] = useState<Array<{ id: string; name: string; category: string; stock: string; change: string; risk: string }>>([]);
  const [forecastTrend, setForecastTrend] = useState<Array<{ period: string; demand: number; inventory: number }>>([]);
  const [riskSignals, setRiskSignals] = useState<Array<{ title: string; description: string; severity: string }>>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [summary, inventoryProducts, trend] = await Promise.all([
        getInventorySummary(),
        listInventoryProducts(search),
        getInventoryForecastTrend(),
      ]);
      setMetrics([
        { label: 'On-hand units', value: summary.on_hand_units.toLocaleString(), detail: `Across ${summary.warehouse_count} hubs` },
        { label: 'Stockout risk', value: `${summary.stockout_risk_pct}%`, detail: 'Target < 10%' },
        { label: 'Demand coverage', value: `${summary.demand_coverage_pct}%`, detail: 'Next 14 days' },
        { label: 'Reorder alerts', value: String(summary.reorder_alerts), detail: 'Priority items' },
      ]);
      setProducts(
        inventoryProducts.map((product) => ({
          id: product.id,
          name: product.name ?? 'Unnamed product',
          category: product.category ?? 'General',
          stock: String(product.stock ?? 0),
          change: (product.stock ?? 0) > 0 ? `${product.stock} units` : '-100%',
          risk: product.status === 'Out of Stock' ? 'Critical' : product.status === 'Low Stock' ? 'High' : 'Stable',
        })),
      );
      setForecastTrend(trend);
      setRiskSignals(summary.risk_signals);
    } catch {
      setMetrics(fallbackMetrics);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [search]);

  const filteredProducts = useMemo(
    () =>
      products.filter((product) => {
        const matchesSearch = (product.name ?? '').toLowerCase().includes(search.toLowerCase());
        const matchesStatus = activeStatus === 'All' || product.risk === activeStatus;
        return matchesSearch && matchesStatus;
      }),
    [search, activeStatus, products],
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section className="mb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Inventory dashboard</p>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Operational stock management</h1>
              <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
                Monitor stock health, fulfilment risk and demand signal performance across your warehouse network.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="outline" className="rounded-full px-4 py-2 text-sm font-medium" onClick={() => void loadData()} disabled={loading}>
                <RefreshCcw className="mr-2 h-4 w-4" /> Refresh snapshot
              </Button>
              <Button className="rounded-full bg-black px-4 py-2 text-sm font-medium text-white">
                <ShieldCheck className="mr-2 h-4 w-4" /> Review thresholds
              </Button>
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {metrics.map((stat) => (
            <div key={stat.label} className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{stat.label}</p>
              <div className="mt-4 flex items-center justify-between gap-4">
                <h2 className="text-3xl font-semibold text-foreground">{stat.value}</h2>
                <div className="rounded-3xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">{stat.detail}</div>
              </div>
            </div>
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr] mb-8 items-stretch">
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm flex flex-col h-full">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Stockout risk matrix</p>
                <p className="text-xs text-muted-foreground">Live demand vs available inventory for high-risk SKUs.</p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {['All', 'Critical', 'High', 'Elevated', 'Stable'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setActiveStatus(status)}
                    className={`rounded-full px-3 py-2 text-xs font-semibold transition ${
                      activeStatus === status ? 'bg-black text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto max-h-[360px] overflow-y-auto">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="border-b border-border bg-background/70">
                  <tr>
                    <th className="px-4 py-3 font-medium text-muted-foreground">SKU</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Category</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Stock level</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Trend</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredProducts.map((product) => (
                    <tr key={product.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-4 font-semibold text-foreground">{product.name}</td>
                      <td className="px-4 py-4 text-muted-foreground">{product.category}</td>
                      <td className="px-4 py-4 text-foreground">{product.stock}</td>
                      <td className="px-4 py-4 text-muted-foreground">{product.change}</td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                          product.risk === 'Critical' ? 'bg-red-50 text-red-700' : product.risk === 'High' ? 'bg-amber-50 text-amber-700' : product.risk === 'Elevated' ? 'bg-sky-50 text-sky-700' : 'bg-emerald-50 text-emerald-700'
                        }`}>
                          {product.risk}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Demand forecast moved here so left column and right column end at same level */}
            <div className="mt-6 rounded-lg bg-slate-50 p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">Demand forecast</p>
                  <p className="text-xs text-muted-foreground">Projected demand and inventory coverage for the next week.</p>
                </div>
                <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">Forecast horizon: 7 days</span>
              </div>
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecastTrend} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#0f172a" stopOpacity={0.16} />
                        <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="period" tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: 16, borderColor: 'var(--border)', boxShadow: '0 12px 30px rgba(15,23,42,0.08)' }} />
                    <Area type="monotone" dataKey="demand" stroke="#0f172a" strokeWidth={3} fill="url(#demandGradient)" />
                    <Area type="monotone" dataKey="inventory" stroke="#16a34a" strokeWidth={3} fill="none" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <aside className="space-y-6 h-full">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Inventory Copilot</p>
                  <p className="text-xs text-muted-foreground">Launch the AI assistant without taking over the page.</p>
                </div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="w-full rounded-3xl bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900 border border-sky-100 hover:bg-sky-100">
                    Open Inventory Copilot
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[90vw] sm:max-w-[980px] p-0">
                  <DialogHeader className="bg-slate-950/5 px-6 py-5">
                    <DialogTitle>Inventory Copilot</DialogTitle>
                    <DialogDescription>Ask about reorder planning, shortage risk, and inbound stock using AI.</DialogDescription>
                  </DialogHeader>
                  <div className="h-[640px]">
                    <AICopilot domain="inventory" />
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <Box className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Reorder recommendations</p>
                  <p className="text-xs text-muted-foreground">Priority items ready to replenish.</p>
                </div>
              </div>
              <ul className="space-y-3">
                {riskSignals.map((signal) => (
                  <li key={signal.title} className="rounded-3xl bg-slate-50 p-4">
                    <p className="font-semibold text-foreground">{signal.title}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{signal.description}</p>
                    <p className="mt-3 inline-flex rounded-full bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">
                      {signal.severity}
                    </p>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <Search className="h-5 w-5 text-slate-700" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Quick search</p>
                  <p className="text-xs text-muted-foreground">Find SKUs and inventory signals quickly.</p>
                </div>
              </div>
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search SKUs, categories or hubs"
                className="rounded-3xl border border-border bg-background px-4 py-3 text-sm"
              />
            </div>
          </aside>
        </section>

        
      </main>
    </div>
  );
}
