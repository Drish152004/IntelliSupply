import { useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import { Bell, AlertTriangle, Clock3, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const notificationItems = [
  {
    id: 'NTF-001',
    title: 'Cold-chain load RT-2850 enters high risk zone',
    description: 'NH-44 congestion is causing temperature exposure alerts for refrigerated cargo bound for Chennai.',
    category: 'Logistics',
    severity: 'Critical',
    location: 'NH-44 / Bengaluru corridor',
    time: '5 min ago',
    status: 'Investigate',
    unread: true,
  },
  {
    id: 'NTF-002',
    title: 'New security access request submitted',
    description: 'Dispatch manager Karthik Iyer requested supervisor-level access for route planning.',
    category: 'Security',
    severity: 'High',
    location: 'Bengaluru HQ',
    time: '18 min ago',
    status: 'Review',
    unread: true,
  },
  {
    id: 'NTF-003',
    title: 'Stockout warning for USB-C Hub 7-in-1',
    description: 'Bengaluru warehouse inventory has dropped to zero units, triggering immediate replenishment.',
    category: 'Inventory',
    severity: 'Critical',
    location: 'Bengaluru WH',
    time: '52 min ago',
    status: 'Restock',
    unread: false,
  },
  {
    id: 'NTF-004',
    title: 'AI insights ready for route planning',
    description: 'Demand surge forecast suggests rerouting 4 shipments to reduce delay exposure.',
    category: 'AI Insights',
    severity: 'Medium',
    location: 'Route network',
    time: '1h ago',
    status: 'Review',
    unread: false,
  },
  {
    id: 'NTF-005',
    title: 'Failed login attempt blocked',
    description: 'Unusual access attempt blocked for user account in the admin portal.',
    category: 'Security',
    severity: 'Medium',
    location: 'Admin portal',
    time: '2h ago',
    status: 'Monitor',
    unread: false,
  },
];

const categoryClasses: Record<string, string> = {
  Logistics: 'bg-sky-50 text-sky-700',
  Security: 'bg-amber-50 text-amber-700',
  Inventory: 'bg-emerald-50 text-emerald-700',
  'AI Insights': 'bg-violet-50 text-violet-700',
};

const severityClasses: Record<string, string> = {
  Critical: 'bg-red-50 text-red-700',
  High: 'bg-amber-50 text-amber-700',
  Medium: 'bg-slate-50 text-slate-700',
  Low: 'bg-emerald-50 text-emerald-700',
};

const tabs = ['All', 'Critical', 'Logistics', 'Inventory', 'Security', 'AI Insights'];

export default function Notifications() {
  const [activeTab, setActiveTab] = useState('All');
  const [search, setSearch] = useState('');
  const [unreadOnly, setUnreadOnly] = useState(false);

  const visibleNotifications = useMemo(
    () =>
      notificationItems.filter((item) => {
        const matchesTab =
          activeTab === 'All' ||
          item.category === activeTab ||
          (activeTab === 'Critical' && item.severity === 'Critical');
        const matchesSearch =
          item.title.toLowerCase().includes(search.toLowerCase()) ||
          item.description.toLowerCase().includes(search.toLowerCase()) ||
          item.location.toLowerCase().includes(search.toLowerCase());
        const matchesUnread = !unreadOnly || item.unread;
        return matchesTab && matchesSearch && matchesUnread;
      }),
    [activeTab, search, unreadOnly],
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="w-full max-w-[1700px] mx-auto px-6 sm:px-8 lg:px-12 py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Communications</p>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Notification center</h1>
            <p className="max-w-3xl mt-2 text-sm leading-6 text-muted-foreground">
              Review operational alerts, incident updates, and action items across logistics, inventory, security, and AI workflows.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              <Bell className="mr-2 h-4 w-4" /> Mark all read
            </Button>
            <Button variant="outline" className="rounded-full px-4 py-2 text-sm font-medium">
              <Clock3 className="mr-2 h-4 w-4" /> View activity log
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.85fr)] xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
          <section className="page-card p-4 sm:p-5">
            <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap gap-2">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-full px-3 py-1.5 text-xs sm:text-sm font-medium transition ${
                      activeTab === tab
                        ? 'bg-slate-950 text-white'
                        : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-[180px] flex-1 sm:max-w-xs">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search alerts"
                    className="pl-10 h-9"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setUnreadOnly((prev) => !prev)}
                  className={`rounded-full px-3 py-1.5 text-xs sm:text-sm font-medium transition ${
                    unreadOnly ? 'bg-amber-50 text-amber-700' : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {unreadOnly ? 'Unread only' : 'All alerts'}
                </button>
              </div>
            </div>

            <div className="space-y-3 py-4">
              {visibleNotifications.map((item) => (
                <article
                  key={item.id}
                  className={`rounded-2xl border border-border bg-white p-4 sm:p-5 shadow-sm transition ${
                    item.unread ? 'ring-1 ring-slate-200 border-slate-300' : ''
                  }`}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`status-chip ${categoryClasses[item.category]}`}>{item.category}</span>
                        <span className={`status-chip ${severityClasses[item.severity]}`}>{item.severity}</span>
                        {item.unread && <span className="status-chip bg-emerald-50 text-emerald-700">Unread</span>}
                      </div>
                      <h2 className="text-base sm:text-lg font-semibold text-foreground">{item.title}</h2>
                      <p className="text-sm leading-6 text-muted-foreground">{item.description}</p>
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span className="rounded-full bg-slate-50 px-3 py-1">{item.location}</span>
                        <span className="rounded-full bg-slate-50 px-3 py-1">{item.time}</span>
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">Action</span>
                      <Button variant="secondary" size="sm" className="rounded-full px-4">
                        {item.status}
                      </Button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <aside className="flex flex-col gap-5 min-w-0">
            <div className="page-card p-5 sm:p-6">
              <div className="flex items-start gap-4 mb-5">
                <div className="rounded-2xl bg-red-50 p-3 shrink-0">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <p className="text-base font-semibold text-foreground">Priority summary</p>
                  <p className="mt-1 text-sm text-muted-foreground">Critical alerts and action items requiring attention.</p>
                </div>
              </div>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="rounded-2xl border border-border bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-foreground">2 critical logistics alerts</p>
                  <p className="mt-2 text-sm leading-6">Temperature and congestion risk need operator review.</p>
                </div>
                <div className="rounded-2xl border border-border bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-foreground">1 security access warning</p>
                  <p className="mt-2 text-sm leading-6">Review access request pending approval.</p>
                </div>
                <div className="rounded-2xl border border-border bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-foreground">AI guidance available</p>
                  <p className="mt-2 text-sm leading-6">Use the AI insights panel to reroute at-risk shipments.</p>
                </div>
              </div>
            </div>

            <div className="page-card p-5 sm:p-6 flex-1">
              <div className="flex items-start gap-4 mb-5">
                <div className="rounded-2xl bg-slate-100 p-3 shrink-0">
                  <Clock3 className="h-6 w-6 text-slate-700" />
                </div>
                <div>
                  <p className="text-base font-semibold text-foreground">Quick actions</p>
                  <p className="mt-1 text-sm text-muted-foreground">Resolve the top alerts first.</p>
                </div>
              </div>
              <div className="space-y-3">
                <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3.5 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                  Acknowledge critical route alert
                </button>
                <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3.5 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                  Review inventory restock plan
                </button>
                <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3.5 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                  Validate security access request
                </button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
