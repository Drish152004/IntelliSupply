import Navbar from '@/components/Navbar';
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const inventoryTrend = [
  { week: 'W1', turnover: 3.4, stockout: 5 },
  { week: 'W2', turnover: 3.7, stockout: 4 },
  { week: 'W3', turnover: 4.1, stockout: 3 },
  { week: 'W4', turnover: 4.4, stockout: 3 },
  { week: 'W5', turnover: 4.6, stockout: 2 },
  { week: 'W6', turnover: 4.9, stockout: 1 },
];

const categoryDistribution = [
  { name: 'Pharma', value: 28 },
  { name: 'Electronics', value: 22 },
  { name: 'FMCG', value: 18 },
  { name: 'Apparel', value: 14 },
  { name: 'Accessories', value: 18 },
];

const topRisks = [
  { product: 'USB-C Hub 7-in-1', risk: 'Critical', gap: '0 units', location: 'Bengaluru WH' },
  { product: 'Wireless Earbuds X3', risk: 'High', gap: '42 units', location: 'Mumbai Park' },
  { product: 'Vitamin C 1000mg', risk: 'Elevated', gap: '68 units', location: 'Delhi Hub' },
];

const pieColors = ['#0f172a', '#0ea5e9', '#16a34a', '#c2410c', '#8b5cf6'];

export default function InventoryAnalytics() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section className="mb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Inventory analytics</p>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Inventory performance</h1>
              <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
                Monitor turnover, stockout pressure, and category distribution with clarity for faster replenishment decisions.
              </p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-900">
              Refresh forecasts
            </button>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-3 mb-8">
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold text-foreground">Turnover index</p>
            <p className="mt-3 text-3xl font-semibold text-black">4.9x</p>
            <p className="mt-3 text-sm text-muted-foreground">Projected inventory turnover for the next 30 days.</p>
          </div>
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold text-foreground">Stockout risk</p>
            <p className="mt-3 text-3xl font-semibold text-black">3%</p>
            <p className="mt-3 text-sm text-muted-foreground">Percentage of SKUs flagged for restock action.</p>
          </div>
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold text-foreground">Availability score</p>
            <p className="mt-3 text-3xl font-semibold text-black">92%</p>
            <p className="mt-3 text-sm text-muted-foreground">Operational readiness across distribution hubs.</p>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.6fr_1fr] mb-8">
          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <p className="text-sm font-semibold text-foreground">Turnover & stockout trend</p>
                <p className="text-xs text-muted-foreground">Weekly performance across inventory KPIs.</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">Stable recovery</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={inventoryTrend} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="4 4" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="week" tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'rgb(100 116 139)', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 16, borderColor: 'var(--border)', boxShadow: '0 12px 30px rgba(15,23,42,0.08)' }} />
                  <Line type="monotone" dataKey="turnover" stroke="#0f172a" strokeWidth={3} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="stockout" stroke="#f59e0b" strokeWidth={3} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <p className="text-sm font-semibold text-foreground">Category mix</p>
                <p className="text-xs text-muted-foreground">Inventory allocation by product category.</p>
              </div>
              <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-medium text-muted-foreground">Allocation</span>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={categoryDistribution} dataKey="value" nameKey="name" innerRadius={44} outerRadius={80} paddingAngle={4}>
                    {categoryDistribution.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={pieColors[index]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
              {categoryDistribution.map((category) => (
                <div key={category.name} className="rounded-3xl border border-border bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">{category.name}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{category.value}% of inventory</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
            <div>
              <p className="text-sm font-semibold text-foreground">Top inventory risk items</p>
              <p className="text-xs text-muted-foreground">Items requiring priority replenishment across hubs.</p>
            </div>
            <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">Critical focus</span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border text-left text-sm">
              <thead className="border-b border-border bg-background/70">
                <tr>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Product</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Risk level</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Gap</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Location</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {topRisks.map((item) => (
                  <tr key={item.product} className="hover:bg-muted/80 transition-colors">
                    <td className="px-4 py-4 font-semibold text-foreground">{item.product}</td>
                    <td className="px-4 py-4">
                      <span className="inline-flex rounded-full bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">{item.risk}</span>
                    </td>
                    <td className="px-4 py-4 text-muted-foreground">{item.gap}</td>
                    <td className="px-4 py-4 text-muted-foreground">{item.location}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
