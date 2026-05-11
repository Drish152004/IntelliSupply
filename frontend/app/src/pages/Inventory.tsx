import { useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import InventoryCopilot from '@/components/InventoryCopilot';

const products = [
  { id: '01', name: 'Paracetamol 500mg', category: 'Pharma', sold: '9,204', share: 90, pct: '19.0%', status: 'In Stock', tag: 'tag-g' },
  { id: '02', name: 'Wireless Earbuds X3', category: 'Electronics', sold: '7,841', share: 76, pct: '16.2%', status: 'Low Stock', tag: 'tag-a' },
  { id: '03', name: 'Basmati Rice 5kg', category: 'FMCG', sold: '6,390', share: 62, pct: '13.2%', status: 'In Stock', tag: 'tag-g' },
  { id: '04', name: 'USB-C Hub 7-in-1', category: 'Electronics', sold: '4,120', share: 40, pct: '8.5%', status: 'Stockout', tag: 'tag-r' },
  { id: '05', name: 'Cotton T-Shirt (M)', category: 'Apparel', sold: '3,765', share: 36, pct: '7.8%', status: 'In Stock', tag: 'tag-g' },
];

const heatmap = [
  ['Bengaluru', [3, 4, 5, 4, 3, 2, 1]],
  ['Chennai', [2, 2, 3, 3, 4, 3, 2]],
  ['Mumbai', [4, 3, 3, 2, 2, 3, 5]],
  ['Delhi', [1, 1, 2, 3, 3, 4, 5]],
] as const;

export default function Inventory() {
  const [isInsightsOpen, setIsInsightsOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const metrics = useMemo(
    () => [
      { label: 'Units Sold', value: '48,320', sub: '↑ 12% vs last month', className: 'up' },
      { label: 'Revenue', value: '₹2.4Cr', sub: '↑ 8.3%', className: 'up' },
      { label: 'Active SKUs', value: '1,204', sub: 'across 6 hubs', className: '' },
      { label: 'Stockout Risk', value: '37', sub: '↑ 5 items flagged', className: 'down' },
    ],
    []
  );

  const refreshModel = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1200);
  };

  return (
    <div className="h-screen bg-white text-black overflow-hidden">
      <Navbar />
      <div className="layout">
        <main className="left custom-scrollbar">
          <div className="panel-header">
            <span className="panel-title">Inventory — Sales Overview</span>
            <span className="link-action">Export CSV ↗</span>
          </div>

          <div className="filter-bar">
            <div className="filter-group">
              <label>Category</label>
              <select className="filter-select"><option>All Categories</option></select>
            </div>
            <div className="filter-group">
              <label>Status</label>
              <select className="filter-select"><option>All Status</option></select>
            </div>
            <div className="filter-group">
              <label>Hub</label>
              <select className="filter-select"><option>All Hubs</option></select>
            </div>
            <div className="filter-search">
              <input className="filter-input" placeholder="Search products..." />
            </div>
          </div>

          <div className="metrics">
            {metrics.map((m) => (
              <div key={m.label} className="metric">
                <div className="metric-label">{m.label}</div>
                <div className="metric-value">{m.value}</div>
                <div className={`metric-sub ${m.className}`}>{m.sub}</div>
              </div>
            ))}
          </div>

          <div className="panel-header">
            <span className="panel-title">Top Selling Products — This Month</span>
            <span className="link-action">View All</span>
          </div>
          <div className="tbl-wrap">
            <table className="inv-table">
              <thead>
                <tr><th>#</th><th>Product</th><th>Category</th><th>Units Sold</th><th>Share</th><th>Status</th></tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id}>
                    <td className="row-num">{p.id}</td>
                    <td className="prod-name">{p.name}</td>
                    <td><span className="tag">{p.category}</span></td>
                    <td>{p.sold}</td>
                    <td>
                      <div style={{ fontSize: 11, marginBottom: 6 }}>{p.pct}</div>
                      <div className="bar-track"><div className="bar-fill" style={{ width: `${p.share}%` }} /></div>
                    </td>
                    <td><span className={`tag ${p.tag}`}>{p.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="forecast-box">
            <div className="forecast-top">
              <div>
                <div className="forecast-label">Demand Forecast — STG Heatmap</div>
                <div className="forecast-sub">Next 7-day demand pressure by zone · Darker = higher pressure</div>
              </div>
              <div className="flex gap-2">
                <button className="btn" onClick={() => setIsInsightsOpen((p) => !p)}>
                  {isInsightsOpen ? '↑ Close Insights' : '↳ Insights & Query'}
                </button>
                <button className="btn btn-dark" onClick={refreshModel}>
                  {refreshing ? '↻ Refreshing...' : '↻ Refresh Model'}
                </button>
              </div>
            </div>
            <div className="heatmap-wrap">
              <div className="hm-grid-header">
                <div />
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => <div key={day} className="hm-col-label">{day}</div>)}
              </div>
              {heatmap.map(([city, scores]) => (
                <div key={city} className="hm-row">
                  <div className="hm-row-label">{city}</div>
                  {scores.map((score, idx) => <div key={`${city}-${idx}`} className={`hm-cell hm-${score}`}>{score === 1 ? 28 : score === 2 ? 50 : score === 3 ? 68 : score === 4 ? 83 : 96}</div>)}
                </div>
              ))}
            </div>
            <div className={`insights-drawer ${isInsightsOpen ? 'open' : ''}`}>
              <div className="insights-inner">
                <div className="insight-cards">
                  <div className="insight-card"><div className="metric-label">Peak Pressure Zone</div><div className="metric-value">Bengaluru</div><div className="metric-sub">Wed · Score 94</div></div>
                  <div className="insight-card"><div className="metric-label">Demand Spike Risk</div><div className="metric-value">Delhi — Sun</div><div className="metric-sub">Score 96</div></div>
                  <div className="insight-card"><div className="metric-label">Lowest Pressure</div><div className="metric-value">Delhi — Tue</div><div className="metric-sub">Score 29</div></div>
                </div>
              </div>
            </div>
          </div>
        </main>
        <InventoryCopilot />
      </div>
    </div>
  );
}
