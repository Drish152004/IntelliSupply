import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import {
  listShipments,
  predictCourierRoute,
  listHubLocations,
  type ShipmentListItem,
  type CourierRouteResult,
  type HubMapLocation,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Calendar,
  Loader2,
  AlertCircle,
  Truck,
  ShieldCheck,
  Route as RouteIcon,
  MapPin,
} from 'lucide-react';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Courier() {
  const { user, loading: authLoading } = useAuth();

  const [shipments, setShipments] = useState<ShipmentListItem[]>([]);
  const [shipmentsLoading, setShipmentsLoading] = useState(false);
  const [deliveryDay, setDeliveryDay] = useState(todayISO());

  const [routeResult, setRouteResult] = useState<CourierRouteResult | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);

  const [hubLocations, setHubLocations] = useState<HubMapLocation[]>([]);
  const [highlightedOrderId, setHighlightedOrderId] = useState<string | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  const [mapMessage, setMapMessage] = useState<string | null>(null);
  const [mapRouteLoading, setMapRouteLoading] = useState(false);

  // Load hub map locations on mount
  useEffect(() => {
    if (authLoading || !user) return;
    void listHubLocations()
      .then(setHubLocations)
      .catch(() => setHubLocations([]));
  }, [authLoading, user]);

  // Load shipments & route on load/date change
  const loadCourierData = async () => {
    if (authLoading || !user) return;

    setShipmentsLoading(true);
    setRouteLoading(true);
    setRouteResult(null);
    setHighlightedOrderId(null);
    setMapMessage(null);

    // 1. Load shipments assigned to me
    try {
      const data = await listShipments({
        limit: 50,
        deliveryDay,
        courierId: 'me',
      });
      setShipments(data);
    } catch {
      setShipments([]);
    } finally {
      setShipmentsLoading(false);
    }

    // 2. Load optimized route
    try {
      const route = await predictCourierRoute('me', deliveryDay);
      setRouteResult(route);
    } catch {
      setRouteResult(null);
    } finally {
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    void loadCourierData();
  }, [authLoading, user, deliveryDay]);

  const mapStats = [
    {
      label: 'Assigned deliveries',
      value: shipmentsLoading ? '—' : String(shipments.length),
    },
    {
      label: 'Total duration',
      value: routeLoading ? '—' : routeResult ? `${routeResult.total_eta_minutes} min` : '—',
    },
    {
      label: 'Total stops',
      value: routeLoading ? '—' : routeResult ? String(routeResult.stops.length) : '—',
    },
  ];

  const shipmentsPanel = (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-5 py-5">
        <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
          <Truck className="h-3.5 w-3.5" />
          Active Operations
        </div>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">My shipments</h2>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Your assigned orders for the selected day.
        </p>
      </div>

      {/* Date Filter */}
      <div className="shrink-0 space-y-2 border-b border-border px-5 py-3">
        <div className="relative">
          <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="date"
            value={deliveryDay}
            onChange={(e) => setDeliveryDay(e.target.value)}
            className="rounded-lg border-border bg-white pl-10 text-sm"
          />
        </div>
      </div>

      {/* Shipment list */}
      <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {shipmentsLoading && (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        )}
        {!shipmentsLoading && shipments.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No shipments assigned for this date.
          </p>
        )}
        {!shipmentsLoading &&
          shipments.map((shipment) => (
            <div
              key={shipment.order_id}
              className={cn(
                'rounded-2xl border p-4 transition-all duration-200',
                highlightedOrderId === shipment.order_id
                  ? 'border-amber-300 bg-gradient-to-br from-amber-50/80 to-sky-50/50 shadow-md shadow-amber-100/60 ring-2 ring-amber-200/80'
                  : 'border-border bg-slate-50/80 hover:border-sky-200 hover:shadow-sm',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{shipment.order_id}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {shipment.from_hub_name} → {shipment.to_hub_name}
                  </p>
                </div>
                <span className="rounded-full bg-amber-50 px-3 py-1 text-[11px] font-semibold text-amber-700">
                  {shipment.status ?? 'In Transit'}
                </span>
              </div>

              <div className="mt-3 flex items-center justify-end gap-3 text-xs text-muted-foreground">
                <button
                  type="button"
                  onClick={() => setHighlightedOrderId(shipment.order_id)}
                  className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 transition-colors hover:bg-sky-100"
                >
                  <MapPin className="h-3 w-3" />
                  Show on map
                </button>
              </div>
            </div>
          ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1750px] flex-col px-5 sm:px-7 lg:px-10 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Courier dashboard
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">My deliveries</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            View your assigned orders, plan your route, and access the Copilot assistant.
          </p>
        </header>

        <div
          className={cn(
            'grid min-h-0 flex-1 gap-6',
            'h-[calc(100dvh-11rem)] min-h-[680px]',
            'grid-cols-1 xl:grid-cols-[minmax(340px,390px)_minmax(0,1fr)_minmax(340px,390px)]',
          )}
        >
          {/* LEFT PANEL */}
          <aside className="page-card flex min-h-0 flex-col overflow-hidden">
            {shipmentsPanel}
          </aside>

          {/* CENTER PANEL */}
          <section className="page-card flex min-h-0 flex-col overflow-hidden p-5">
            <div className="shrink-0 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                  Map-first operations
                </p>
                <h2 className="mt-1 text-2xl font-semibold">Operational map</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="status-chip bg-emerald-50 text-emerald-700">On time</span>
                <span className="status-chip bg-amber-50 text-amber-700">Delayed</span>
                <span className="status-chip bg-red-50 text-red-700">Critical</span>
              </div>
            </div>

            <div className="mt-4 grid shrink-0 grid-cols-3 gap-3 overflow-hidden rounded-xl border border-border bg-slate-50">
              {mapStats.map((stat, index) => (
                <div
                  key={stat.label}
                  className={cn('px-4 py-3.5', index < 2 && 'border-r border-border')}
                >
                  <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                    {stat.label}
                  </p>
                  <p className="mt-1.5 text-xl font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>

            <div className="relative z-0 isolate mt-4 min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-inner shadow-slate-100">
              {mapMessage && (
                <div className="absolute inset-x-3 top-3 z-[30] flex justify-center">
                  <span className="inline-flex max-w-md items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/95 px-3 py-2 text-xs font-medium text-amber-900 shadow-sm">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {mapMessage}
                  </span>
                </div>
              )}
              {mapRouteLoading && (
                <div className="absolute inset-x-0 top-3 z-[30] flex justify-center">
                  <span className="inline-flex items-center gap-2 rounded-full border border-sky-200/80 bg-white/95 px-4 py-2 text-xs font-medium text-sky-800 shadow-lg shadow-sky-100/50 backdrop-blur-sm">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
                    Plotting route…
                  </span>
                </div>
              )}
              <RouteMap
                selectedRouteId={selectedRouteId}
                onRouteSelect={setSelectedRouteId}
                activeCourierRoute={routeResult}
                highlightedOrderId={highlightedOrderId}
                onStopSelect={setHighlightedOrderId}
                showDemoRoutes={false}
                hubLocations={hubLocations}
                chinaMapOnly
              />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6 flex flex-col min-h-0">
            {/* Copilot */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm shrink-0">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Logistics Copilot</p>
                  <p className="text-xs text-muted-foreground">
                    Open the AI assistant in a dedicated view.
                  </p>
                </div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="w-full rounded-3xl bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900 border border-sky-100 hover:bg-sky-100">
                    Open Logistics Copilot
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[90vw] sm:max-w-[980px] p-0">
                  <DialogHeader className="bg-slate-950/5 px-6 py-5">
                    <DialogTitle>Logistics Copilot</DialogTitle>
                    <DialogDescription>
                      Ask about your route sequence, delays, and deliveries.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="h-[640px]">
                    <AICopilot />
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* Route Stops Sequence */}
            <div className="page-card flex min-h-0 flex-1 flex-col overflow-hidden p-0">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Optimized Sequence
                </p>
                <h2 className="text-base font-semibold">Route details</h2>
              </div>

              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto custom-scrollbar p-4">
                {routeLoading && (
                  <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
                    Loading route stops…
                  </div>
                )}
                {!routeLoading && !routeResult && (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No active route sequence found.
                  </p>
                )}
                {!routeLoading &&
                  routeResult &&
                  routeResult.stops.map((stop) => (
                    <div
                      key={stop.order_id}
                      onClick={() => setHighlightedOrderId(stop.order_id)}
                      className={cn(
                        'rounded-xl border p-3 text-sm transition cursor-pointer',
                        highlightedOrderId === stop.order_id
                          ? 'border-amber-300 bg-amber-50/50 shadow-sm ring-1 ring-amber-200'
                          : 'border-border bg-slate-50/60 hover:border-sky-200',
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-xs text-muted-foreground">
                          Stop #{stop.sequence}
                        </span>
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                          {stop.eta_minutes} min
                        </span>
                      </div>
                      <p className="mt-1.5 font-semibold text-xs font-mono">{stop.order_id}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {stop.from_hub_name} → {stop.to_hub_name}
                      </p>
                      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>From start: +{stop.eta_from_start_minutes}m</span>
                        <span className="font-medium text-slate-800">Arrival: {stop.estimated_arrival}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}