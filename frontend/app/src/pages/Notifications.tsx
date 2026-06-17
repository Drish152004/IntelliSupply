import { useEffect, useMemo, useState } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import Navbar from '@/components/Navbar';
import { Bell, AlertTriangle, Clock3, Search, Package, Truck, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from '@/lib/api';

const ROLE_TABS: Record<string, string[]> = {
  admin: ['All', 'Critical', 'Logistics', 'Route Alerts', 'Dispatch', 'Inventory', 'Stock Alerts', 'AI Insights'],
  logistics_manager: ['All', 'Critical', 'Logistics', 'Route Alerts', 'Dispatch', 'AI Insights'],
  inventory_manager: ['All', 'Critical', 'Inventory', 'Stock Alerts'],
  courier: ['All', 'Critical', 'Dispatch', 'Route Alerts'],
};

const ROLE_CATEGORIES: Record<string, string[]> = {
  admin: ['Logistics', 'Route Alerts', 'Dispatch', 'Inventory', 'Stock Alerts', 'AI Insights'],
  logistics_manager: ['Logistics', 'Route Alerts', 'Dispatch', 'AI Insights'],
  inventory_manager: ['Inventory', 'Stock Alerts'],
  courier: ['Dispatch', 'Route Alerts'],
};

const categoryClasses: Record<string, string> = {
  Logistics: 'bg-sky-50 text-sky-700',
  'Route Alerts': 'bg-blue-50 text-blue-700',
  Dispatch: 'bg-violet-50 text-violet-700',
  Inventory: 'bg-emerald-50 text-emerald-700',
  'Stock Alerts': 'bg-orange-50 text-orange-700',
  'AI Insights': 'bg-purple-50 text-purple-700',
};

const severityClasses: Record<string, string> = {
  Critical: 'bg-red-50 text-red-700',
  High: 'bg-amber-50 text-amber-700',
  Medium: 'bg-slate-50 text-slate-700',
  Low: 'bg-emerald-50 text-emerald-700',
};

function normalizeSeverity(severity?: string): string {
  if (!severity) return 'Medium';
  const value = severity.toLowerCase();

  if (value === 'critical') return 'Critical';
  if (value === 'high') return 'High';
  if (value === 'low') return 'Low';
  return 'Medium';
}

function getCategory(item: NotificationItem): string {
  const alertType = item.alert_type?.toLowerCase() ?? '';
  const source = item.source?.toLowerCase() ?? '';

  if (alertType.includes('route')) return 'Route Alerts';
  if (alertType.includes('order') || alertType.includes('shipment')) return 'Dispatch';
  if (alertType.includes('courier')) return 'Logistics';
  if (alertType.includes('stock') || alertType.includes('inventory')) return 'Stock Alerts';
  if (alertType.includes('demand') || alertType.includes('forecast')) return 'AI Insights';
  if (source.includes('ml')) return 'AI Insights';
  return 'Logistics';
}

function formatTime(createdAt?: string): string {
  if (!createdAt) return 'recent';

  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return 'recent';

  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getActionLabel(item: NotificationItem): string {
  const alertType = item.alert_type?.toLowerCase() ?? '';

  if (item.is_read) return 'Read';
  if (alertType.includes('stock')) return 'Restock';
  if (alertType.includes('route')) return 'Review route';
  if (alertType.includes('order')) return 'Review order';
  if (alertType.includes('courier')) return 'Review courier';
  return 'Review';
}

export default function Notifications() {
  const { user } = useAuth();
  const role = user?.role ?? 'admin';

  const tabs = ROLE_TABS[role] ?? ROLE_TABS.admin;
  const allowedCategories = ROLE_CATEGORIES[role] ?? ROLE_CATEGORIES.admin;

  const [activeTab, setActiveTab] = useSessionStorageState('notifications_active_tab', 'All');
  const [search, setSearch] = useSessionStorageState('notifications_search', '');
  const [unreadOnly, setUnreadOnly] = useSessionStorageState('notifications_unread_only', false);
  const [notificationItems, setNotificationItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadNotifications() {
    setLoading(true);
    try {
      const items = await listNotifications(50);
      setNotificationItems(items);
    } catch {
      setNotificationItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadNotifications();
  }, []);

  async function handleMarkOneRead(notificationId: string) {
    try {
      const updated = await markNotificationRead(notificationId);
      setNotificationItems((items) =>
        items.map((item) =>
          item.notification_id === notificationId ? updated : item,
        ),
      );
    } catch {
      // keep UI stable if backend fails
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      setNotificationItems((items) =>
        items.map((item) => ({
          ...item,
          is_read: true,
        })),
      );
    } catch {
      // keep UI stable if backend fails
    }
  }

  const visibleNotifications = useMemo(
    () =>
      notificationItems.filter((item) => {
        const category = getCategory(item);
        const severity = normalizeSeverity(item.severity);
        const message = item.message ?? '';
        const relatedEntity = item.related_entity_id ?? '';

        const matchesRole = allowedCategories.includes(category);
        const matchesTab =
          activeTab === 'All' ||
          category === activeTab ||
          (activeTab === 'Critical' && severity === 'Critical');

        const searchValue = search.toLowerCase();
        const matchesSearch =
          item.title.toLowerCase().includes(searchValue) ||
          message.toLowerCase().includes(searchValue) ||
          relatedEntity.toLowerCase().includes(searchValue) ||
          category.toLowerCase().includes(searchValue);

        const matchesUnread = !unreadOnly || !item.is_read;

        return matchesRole && matchesTab && matchesSearch && matchesUnread;
      }),
    [activeTab, search, unreadOnly, allowedCategories, notificationItems],
  );

  const criticalCount = visibleNotifications.filter(
    (item) => normalizeSeverity(item.severity) === 'Critical',
  ).length;

  const unreadCount = visibleNotifications.filter((item) => !item.is_read).length;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="w-full max-w-[1700px] mx-auto px-6 sm:px-8 lg:px-12 py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground mb-1.5">
              Communications
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              Notification center
            </h1>
            <p className="max-w-3xl mt-1.5 text-sm leading-6 text-muted-foreground">
              {role === 'logistics_manager'
                ? 'Logistics alerts, route events, dispatch issues, and AI insights.'
                : role === 'inventory_manager'
                  ? 'Inventory alerts, stock warnings, and reorder recommendations.'
                  : role === 'courier'
                    ? 'Assigned orders, route alerts, and delivery updates.'
                    : 'Review operational alerts across logistics, inventory, and AI workflows.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={handleMarkAllRead}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              <Bell className="mr-2 h-4 w-4" />
              Mark all read
            </Button>

            <Button
              variant="outline"
              onClick={loadNotifications}
              className="rounded-full px-4 py-2 text-sm font-medium"
            >
              <Clock3 className="mr-2 h-4 w-4" />
              Refresh
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
                    unreadOnly
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {unreadOnly ? 'Unread only' : 'All alerts'}
                </button>
              </div>
            </div>

            <div className="space-y-3 py-4">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <RotateCcw className="h-8 w-8 animate-spin text-slate-300" />
                  <p className="mt-3 text-sm font-medium text-slate-500">
                    Loading notifications...
                  </p>
                </div>
              ) : visibleNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <RotateCcw className="h-8 w-8 text-slate-300" />
                  <p className="mt-3 text-sm font-medium text-slate-500">
                    No alerts match your filters.
                  </p>
                </div>
              ) : (
                visibleNotifications.map((item) => {
                  const category = getCategory(item);
                  const severity = normalizeSeverity(item.severity);
                  const isUnread = !item.is_read;

                  return (
                    <article
                      key={item.notification_id}
                      className={`rounded-2xl border border-border bg-white p-4 sm:p-5 shadow-sm transition ${
                        isUnread ? 'ring-1 ring-slate-200 border-slate-300' : ''
                      }`}
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`status-chip ${categoryClasses[category] ?? 'bg-slate-50 text-slate-700'}`}>
                              {category}
                            </span>

                            <span className={`status-chip ${severityClasses[severity] ?? severityClasses.Medium}`}>
                              {severity}
                            </span>

                            {isUnread && (
                              <span className="status-chip bg-emerald-50 text-emerald-700">
                                Unread
                              </span>
                            )}
                          </div>

                          <h2 className="text-sm font-semibold text-foreground sm:text-base">
                            {item.title}
                          </h2>

                          <p className="text-sm leading-6 text-muted-foreground">
                            {item.message}
                          </p>

                          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                            <span className="rounded-full bg-slate-50 px-3 py-1">
                              {item.related_entity_type ?? 'system'}
                              {item.related_entity_id ? `: ${item.related_entity_id}` : ''}
                            </span>

                            <span className="rounded-full bg-slate-50 px-3 py-1">
                              {formatTime(item.created_at)}
                            </span>

                            {item.source && (
                              <span className="rounded-full bg-slate-50 px-3 py-1">
                                {item.source}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                          <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                            Action
                          </span>

                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={!isUnread}
                            onClick={() => handleMarkOneRead(item.notification_id)}
                            className="rounded-full px-4"
                          >
                            {getActionLabel(item)}
                          </Button>
                        </div>
                      </div>
                    </article>
                  );
                })
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
                  <p className="text-sm font-semibold text-foreground">
                    Priority summary
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {criticalCount > 0
                      ? `${criticalCount} critical alert${criticalCount > 1 ? 's' : ''} need attention.`
                      : 'No critical alerts right now.'}
                  </p>
                </div>
              </div>

              <div className="space-y-3 text-sm text-muted-foreground">
                {role !== 'inventory_manager' && (
                  <div className="rounded-2xl border border-border bg-slate-50 p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Truck className="h-4 w-4 text-sky-600" />
                      <p className="text-sm font-semibold text-foreground">
                        Logistics alerts
                      </p>
                    </div>
                    <p className="text-sm leading-6">
                      Route predictions, courier assignment, and dispatch activity.
                    </p>
                  </div>
                )}

                {role !== 'logistics_manager' && role !== 'courier' && (
                  <div className="rounded-2xl border border-border bg-slate-50 p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Package className="h-4 w-4 text-emerald-600" />
                      <p className="text-sm font-semibold text-foreground">
                        Inventory alerts
                      </p>
                    </div>
                    <p className="text-sm leading-6">
                      Stock warnings, reorder alerts, and inventory updates.
                    </p>
                  </div>
                )}

                {unreadCount > 0 && (
                  <div className="rounded-2xl border border-border bg-amber-50/80 p-4">
                    <p className="text-sm font-semibold text-amber-900">
                      {unreadCount} unread
                    </p>
                    <p className="mt-1 text-sm text-amber-800">
                      Mark all read to clear the queue.
                    </p>
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
                  <p className="text-sm font-semibold text-foreground">
                    Quick actions
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Resolve the top alerts first.
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                {role !== 'inventory_manager' && (
                  <button
                    type="button"
                    className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition"
                  >
                    Review latest dispatch alerts
                  </button>
                )}

                {role !== 'logistics_manager' && role !== 'courier' && (
                  <button
                    type="button"
                    className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition"
                  >
                    Review inventory restock plan
                  </button>
                )}

                <button
                  type="button"
                  onClick={loadNotifications}
                  className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-foreground hover:border-slate-300 hover:bg-slate-50 transition"
                >
                  Refresh notification feed
                </button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}