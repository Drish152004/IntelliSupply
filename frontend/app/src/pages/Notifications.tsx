import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import { Bell, AlertTriangle, Clock3, Search, Package, Truck, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth';
import { listNotifications, type NotificationItem } from '@/lib/api';

// ─── Role tab config ──────────────────────────────────────────────────────────

const ROLE_TABS: Record<string, string[]> = {
  admin: ['All', 'Critical', 'Logistics', 'Route Alerts', 'Dispatch', 'Inventory', 'Reorder Alerts', 'Stock Alerts', 'AI Insights'],
  logistics_manager: ['All', 'Critical', 'Logistics', 'Route Alerts', 'Dispatch', 'AI Insights'],
  inventory_manager: ['All', 'Critical', 'Inventory', 'Stock Alerts', 'Reorder Alerts'],
};

const ROLE_CATEGORIES: Record<string, string[]> = {
  admin: ['Logistics', 'Route Alerts', 'Dispatch', 'Inventory', 'Reorder Alerts', 'Stock Alerts', 'AI Insights'],
  logistics_manager: ['Logistics', 'Route Alerts', 'Dispatch', 'AI Insights'],
  inventory_manager: ['Inventory', 'Stock Alerts', 'Reorder Alerts'],
};

// ─── Style maps ───────────────────────────────────────────────────────────────

const categoryClasses: Record<string, string> = {
  Logistics: 'bg-sky-50 text-sky-700',
  'Route Alerts': 'bg-blue-50 text-blue-700',
  Dispatch: 'bg-violet-50 text-violet-700',
  Inventory: 'bg-emerald-50 text-emerald-700',
  'Reorder Alerts': 'bg-teal-50 text-teal-700',
  'Stock Alerts': 'bg-orange-50 text-orange-700',
  'AI Insights': 'bg-purple-50 text-purple-700',
};

const severityClasses: Record<string, string> = {
  Critical: 'bg-red-50 text-red-700',
  High: 'bg-amber-50 text-amber-700',
  Medium: 'bg-slate-50 text-slate-700',
  Low: 'bg-emerald-50 text-emerald-700',
};

export default function Notifications() {
  const { user } = useAuth();
  const role = user?.role ?? 'admin';

  const tabs = ROLE_TABS[role] ?? ROLE_TABS.admin;
  const allowedCategories = ROLE_CATEGORIES[role] ?? ROLE_CATEGORIES.admin;

  const [activeTab, setActiveTab] = useState('All');
  const [search, setSearch] = useState('');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [notificationItems, setNotificationItems] = useState<NotificationItem[]>([]);

  useEffect(() => {
    void listNotifications()
      .then(setNotificationItems)
      .catch(() => setNotificationItems([]));
  }, []);

  const visibleNotifications = useMemo(
    () =>
      notificationItems.filter((item) => {
        // Role filter — non-admins only see their categories
        const matchesRole = allowedCategories.includes(item.category);
        const matchesTab =
          activeTab === 'All' ||
          item.category === activeTab ||
          (activeTab === 'Critical' && item.severity === 'Critical');
        const matchesSearch =
          item.title.toLowerCase().includes(search.toLowerCase()) ||
          item.description.toLowerCase().includes(search.toLowerCase()) ||
          item.location.toLowerCase().includes(search.toLowerCase());
        const matchesUnread = !unreadOnly || item.unread;
        return matchesRole && matchesTab && matchesSearch && matchesUnread;
      }),
    [activeTab, search, unreadOnly, allowedCategories, notificationItems],
  );

  const criticalCount = visibleNotifications.filter((n) => n.severity === 'Critical').length;
  const unreadCount = visibleNotifications.filter((n) => n.unread).length;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="w-full max-w-[1700px] mx-auto px-6 sm:px-8 lg:px-12 py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground mb-1.5">Communications</p>
            <h1 className="text-3xl font-semibold tracking-tight">Notification center</h1>
            <p className="max-w-3xl mt-1.5 text-sm leading-6 text-muted-foreground">
              {role === 'logistics_manager'
                ? 'Logistics alerts, route events, dispatch issues, and AI insights.'
                : role === 'inventory_manager'
                ? 'Inventory alerts, stock warnings, and reorder recommendations.'
                : 'Review operational alerts across logistics, inventory, and AI workflows.'}
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
              <div className="flex flex-wrap gap-1.5">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
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
                <div className="relative min-w-[160px] flex-1 sm:max-w-xs">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search alerts"
                    className="pl-9 h-9"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setUnreadOnly((prev) => !prev)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    unreadOnly ? 'bg-amber-50 text-amber-700' : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {unreadOnly ? 'Unread only' : 'All alerts'}
                </button>
              </div>
            </div>

            <div className="space-y-3 py-4">
              {visibleNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <RotateCcw className="h-8 w-8 text-slate-300" />
                  <p className="mt-3 text-sm font-medium text-slate-500">No alerts match your filters.</p>
                </div>
              ) : (
                visibleNotifications.map((item) => (
                  <article
                    key={item.id}
                    className={`rounded-2xl border border-border bg-white p-4 sm:p-5 shadow-sm transition ${
                      item.unread ? 'ring-1 ring-slate-200 border-slate-300' : ''
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`status-chip ${categoryClasses[item.category] ?? 'bg-slate-50 text-slate-700'}`}>{item.category}</span>
                          <span className={`status-chip ${severityClasses[item.severity]}`}>{item.severity}</span>
                          {item.unread && <span className="status-chip bg-emerald-50 text-emerald-700">Unread</span>}
                        </div>
                        <h2 className="text-sm font-semibold text-foreground sm:text-base">{item.title}</h2>
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
                ))
              )}
            </div>
          </section>

          <aside className="flex flex-col gap-5 min-w-0">
            <div className="page-card p-5 sm:p-6">
              <div className="flex items-start gap-4 mb-5">
                <div className="rounded-2xl bg-red-50 p-3 shrink-0">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Priority summary</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {criticalCount > 0 ? `${criticalCount} critical alert${criticalCount > 1 ? 's' : ''} need attention.` : 'No critical alerts right now.'}
                  </p>
                </div>
              </div>
              <div className="space-y-3 text-sm text-muted-foreground">
                {role !== 'inventory_manager' && (
                  <div className="rounded-2xl border border-border bg-slate-50 p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Truck className="h-4 w-4 text-sky-600" />
                      <p className="text-sm font-semibold text-foreground">Logistics alerts</p>
                    </div>
                    <p className="text-sm leading-6">Route deviations and cold-chain risks require dispatch review.</p>
                  </div>
                )}
                {role !== 'logistics_manager' && (
                  <div className="rounded-2xl border border-border bg-slate-50 p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Package className="h-4 w-4 text-emerald-600" />
                      <p className="text-sm font-semibold text-foreground">Inventory alerts</p>
                    </div>
                    <p className="text-sm leading-6">USB-C Hub stockout and Vitamin C reorder need action.</p>
                  </div>
                )}
                {unreadCount > 0 && (
                  <div className="rounded-2xl border border-border bg-amber-50/80 p-4">
                    <p className="text-sm font-semibold text-amber-900">{unreadCount} unread</p>
                    <p className="mt-1 text-sm text-amber-800">Mark all read to clear the queue.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="page-card p-5 sm:p-6 flex-1">
              <div className="flex items-start gap-4 mb-5">
                <div className="rounded-2xl bg-slate-100 p-3 shrink-0">
                  <Clock3 className="h-5 w-5 text-slate-700" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Quick actions</p>
                  <p className="mt-1 text-xs text-muted-foreground">Resolve the top alerts first.</p>
                </div>
              </div>
              <div className="space-y-2.5">
                {role !== 'inventory_manager' && (
                  <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                    Acknowledge critical route alert
                  </button>
                )}
                {role !== 'logistics_manager' && (
                  <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                    Review inventory restock plan
                  </button>
                )}
                {role !== 'inventory_manager' && (
                  <button type="button" className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition">
                    Reassign dispatch slot — Hub_3
                  </button>
                )}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
