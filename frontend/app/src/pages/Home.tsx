import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { CitySelect, HubSelect } from '@/components/logistics/LocationSelect';
import { useLogisticsLocations } from '@/hooks/useLogisticsLocations';
import {
  createShipment,
  getShipment,
  listShipments,
  listDeliveryDays,
  listCouriersWithOrders,
  predictCourierRoute,
  type CourierListItem,
  type CourierRouteResult,
  type OrderDetail,
  type ShipmentListItem,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Plus,
  Sparkles,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Truck,
  ShieldCheck,
  Route,
  ChevronDown,
  MapPin,
} from 'lucide-react';

const dispatchChecklist = [
  'Verify cargo documentation',
  'Confirm hub slot availability',
  'Assign driver and vehicle',
];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatRouteStartTime(routeStartTime?: string | null): string {
  if (!routeStartTime) return '—';
  if (routeStartTime.length >= 16) return routeStartTime.slice(11, 16);
  if (routeStartTime.length >= 5) return routeStartTime.slice(0, 5);
  return routeStartTime;
}

export default function LogisticsDashboard() {
  const { user, loading: authLoading } = useAuth();
  const isManager = user?.role === 'admin' || user?.role === 'logistics_manager';
  const isCourier = user?.role === 'courier';

  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [highlightedOrderId, setHighlightedOrderId] = useState<string | null>(null);
  const [mapRouteLoading, setMapRouteLoading] = useState(false);

  // ── Add-shipment form (managers only) ────────────────────────────────────
  const [showShipmentForm, setShowShipmentForm] = useState(true);
  const [shipmentCityName, setShipmentCityName] = useState('');
  const [fromHubName, setFromHubName] = useState('');
  const [toHubName, setToHubName] = useState('');
  const { cities: shipmentCities, hubs: shipmentHubs, loadingHubs: shipmentHubsLoading } =
    useLogisticsLocations(shipmentCityName);
  const [deliveryDate, setDeliveryDate] = useState('');
  const [receiptTime, setReceiptTime] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{
    orderId: string;
    courierId?: string;
    courierName?: string;
    courierHub?: string;
  } | null>(null);

  // ── Current shipments panel ────────────────────────────────────────────
  const [currentShipments, setCurrentShipments] = useState<ShipmentListItem[]>([]);
  const [shipmentsLoading, setShipmentsLoading] = useState(false);
  const [filterDeliveryDay, setFilterDeliveryDay] = useState(todayISO());
  const [deliveryDaysLoaded, setDeliveryDaysLoaded] = useState(false);
  const [mapMessage, setMapMessage] = useState<string | null>(null);

  // Manager courier dropdown
  const [couriers, setCouriers] = useState<CourierListItem[]>([]);
  const [selectedCourierId, setSelectedCourierId] = useState<string>('');

  // ── Order detail dialog ────────────────────────────────────────────────
  const [detailOpen, setDetailOpen] = useState(false);
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // ── Route dialog ───────────────────────────────────────────────────────
  const [routeOpen, setRouteOpen] = useState(false);
  const [routeResult, setRouteResult] = useState<CourierRouteResult | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  useEffect(() => {
    setRouteResult(null);
    setHighlightedOrderId(null);
  }, [selectedCourierId, filterDeliveryDay]);

  // Pick a delivery day that actually has shipments (today if available, else latest).
  useEffect(() => {
    if (authLoading || !user) return;
    void listDeliveryDays()
      .then((days) => {
        if (!days.length) return;
        const today = todayISO();
        setFilterDeliveryDay((prev) => {
          if (prev && days.includes(prev)) return prev;
          if (days.includes(today)) return today;
          return days[0];
        });
      })
      .catch(() => {
        // Keep today as fallback.
      })
      .finally(() => setDeliveryDaysLoaded(true));
  }, [authLoading, user]);

  // ── Load couriers with orders for the selected delivery day ───────────
  useEffect(() => {
    if (!isManager || !deliveryDaysLoaded) return;
    const day = filterDeliveryDay || todayISO();
    void listCouriersWithOrders(day)
      .then((rows) => {
        setCouriers(rows);
        setSelectedCourierId((prev) =>
          prev && rows.some((c) => c.courier_id === prev) ? prev : '',
        );
      })
      .catch(() => {
        setCouriers([]);
        setSelectedCourierId('');
      });
  }, [isManager, filterDeliveryDay, deliveryDaysLoaded]);

  // ── Load shipments (role-aware) ───────────────────────────────────────
  const loadShipments = () => {
    if (authLoading || !user || !deliveryDaysLoaded) return;
    setShipmentsLoading(true);
    void listShipments({
      limit: 50,
      courierId: isManager && selectedCourierId ? selectedCourierId : undefined,
      deliveryDay: filterDeliveryDay || undefined,
    })
      .then(setCurrentShipments)
      .catch(() => setCurrentShipments([]))
      .finally(() => setShipmentsLoading(false));
  };

  useEffect(() => {
    loadShipments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, filterDeliveryDay, selectedCourierId, deliveryDaysLoaded]);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  // ── View order detail ─────────────────────────────────────────────────
  const handleViewDetails = async (orderId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setOrderDetail(null);
    try {
      const order = await getShipment(orderId);
      setOrderDetail(order);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load order details.');
    } finally {
      setDetailLoading(false);
    }
  };

  // ── Create shipment ────────────────────────────────────────────────────
  const handleShipmentCityChange = (city: string) => {
    setShipmentCityName(city);
    setFromHubName('');
    setToHubName('');
  };

  const handleFromHubChange = (hub: string) => {
    setFromHubName(hub);
    if (toHubName === hub) {
      setToHubName('');
    }
  };

  const handleCreateShipment = async () => {
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    if (!shipmentCityName || !fromHubName || !toHubName) {
      setError('Please select a city, source hub, and destination hub.');
      setSubmitting(false);
      return;
    }
    if (fromHubName === toHubName) {
      setError('Source and destination hubs must be different.');
      setSubmitting(false);
      return;
    }
    try {
      let receiptTimeFormatted: string | undefined;
      if (receiptTime) {
        receiptTimeFormatted = receiptTime.length === 5 ? `${receiptTime}:00` : receiptTime;
      }
      const result = await createShipment({
        from_hub_name: fromHubName.trim(),
        to_hub_name: toHubName.trim(),
        delivery_date: deliveryDate,
        receipt_time: receiptTimeFormatted,
        notes: notes.trim() || undefined,
      });
      setSuccess({
        orderId: result.order?.order_id ?? '',
        courierId: result.order?.assigned_courier_id,
        courierName: result.order?.assigned_courier_name,
        courierHub: result.order?.assigned_courier_hub_name,
      });
      loadShipments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create shipment.');
    } finally {
      setSubmitting(false);
    }
  };

  const loadCourierRoute = async (
    courierId: 'me' | string,
    options: { openDialog?: boolean; highlightOrderId?: string | null } = {},
  ) => {
    const { openDialog = true, highlightOrderId = null } = options;
    if (openDialog) {
      setRouteOpen(true);
      setRouteLoading(true);
      setRouteError(null);
      setRouteResult(null);
    } else {
      setMapRouteLoading(true);
    }

    try {
      const result = await predictCourierRoute(courierId, filterDeliveryDay || todayISO());
      setRouteResult(result);
      setHighlightedOrderId(highlightOrderId);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Route prediction failed.';
      if (openDialog) {
        setRouteError(message);
      }
      throw err;
    } finally {
      if (openDialog) {
        setRouteLoading(false);
      } else {
        setMapRouteLoading(false);
      }
    }
  };

  // ── Predict route ──────────────────────────────────────────────────────
  const handlePredictRoute = async (courierId: 'me' | string) => {
    await loadCourierRoute(courierId, { openDialog: true });
  };

  const handleShowShipmentOnMap = async (shipment: ShipmentListItem) => {
    setMapMessage(null);
    const courierId = isCourier ? 'me' : shipment.assigned_courier_id;
    if (!courierId) {
      setMapMessage('This shipment has no assigned courier yet — assign a courier to show it on the map.');
      return;
    }

    const activeCourierId =
      courierId === 'me' ? user?.courier_id ?? 'me' : courierId;

    if (!routeResult || routeResult.courier_id !== activeCourierId) {
      try {
        await loadCourierRoute(courierId, {
          openDialog: false,
          highlightOrderId: shipment.order_id,
        });
      } catch (err) {
        setMapMessage(
          err instanceof Error ? err.message : 'Could not load courier route for this shipment.',
        );
        setHighlightedOrderId(shipment.order_id);
      }
    } else {
      setHighlightedOrderId(shipment.order_id);
    }
  };

  // ── Current shipments panel content ───────────────────────────────────
  const shipmentsPanel = (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-5 py-5">
        <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
          <Truck className="h-3.5 w-3.5" />
          Active operations
        </div>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">
          {isCourier ? 'My shipments' : 'Current shipments'}
        </h2>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {isCourier
            ? 'Your assigned orders for the selected day.'
            : 'Live dispatches across operational hubs.'}
        </p>
      </div>

      {/* Filters */}
      <div className="shrink-0 space-y-2 border-b border-border px-5 py-3">
        {/* Manager: courier selector */}
        {isManager && (
          <div className="relative">
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <select
              value={selectedCourierId}
              onChange={(e) => setSelectedCourierId(e.target.value)}
              className="w-full appearance-none rounded-lg border border-border bg-slate-50 py-2 pl-3 pr-8 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              <option value="">All couriers with orders</option>
              {couriers.map((c) => (
                <option key={c.courier_id} value={c.courier_id}>
                  {c.name || c.email}
                  {c.email && c.name ? ` (${c.email})` : ''}
                  {c.order_count != null ? ` — ${c.order_count} order${c.order_count === 1 ? '' : 's'}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Delivery day picker */}
        <div className="relative">
          <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="date"
            value={filterDeliveryDay}
            onChange={(e) => setFilterDeliveryDay(e.target.value)}
            className="rounded-lg border-border bg-white pl-10 text-sm"
          />
        </div>
      </div>

      {/* Shipment cards */}
      <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {shipmentsLoading && (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        )}
        {!shipmentsLoading && currentShipments.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No shipments found for the selected filters.
          </p>
        )}
        {!shipmentsLoading &&
          currentShipments.map((shipment) => (
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

              <div className="mt-4 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                <span>
                  Courier:{' '}
                  {shipment.assigned_courier_name ?? shipment.assigned_courier_id ?? 'Unassigned'}
                </span>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void handleShowShipmentOnMap(shipment)}
                    className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 transition-colors hover:bg-sky-100"
                  >
                    <MapPin className="h-3 w-3" />
                    Show on map
                  </button>
                  {isManager && (
                    <button
                      type="button"
                      onClick={() => void handleViewDetails(shipment.order_id)}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      View details
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
      </div>

      {/* Bottom action */}
      <div className="shrink-0 border-t border-border px-5 py-4 space-y-2">
        {isCourier && (
          <Button
            type="button"
            onClick={() => void handlePredictRoute('me')}
            className="flex w-full items-center rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white hover:bg-sky-700"
          >
            <Route className="mr-2 h-4 w-4 shrink-0" />
            My route
            <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
          </Button>
        )}
        {isManager && selectedCourierId && (
          <Button
            type="button"
            onClick={() => void handlePredictRoute(selectedCourierId)}
            className="flex w-full items-center rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white hover:bg-sky-700"
          >
            <Route className="mr-2 h-4 w-4 shrink-0" />
            View route &amp; ETA
            <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1750px] flex-col px-5 sm:px-7 lg:px-10 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Operations
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {isCourier ? 'My deliveries' : 'Logistics command center'}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {isCourier
              ? 'View your assigned orders and plan your delivery route.'
              : 'Create shipments, monitor routes on the live map, and resolve delays with AI-assisted dispatch.'}
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
            {isCourier ? (
              // Couriers see shipments only — no add shipment toggle
              shipmentsPanel
            ) : (
              <>
                {/* Manager toggle */}
                <div className="border-b border-border px-5 pt-5 pb-4">
                  <div className="flex items-center justify-between rounded-2xl border border-border bg-slate-50 p-1">
                    <button
                      onClick={() => setShowShipmentForm(true)}
                      className={cn(
                        'flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold transition',
                        showShipmentForm
                          ? 'bg-black text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-100',
                      )}
                    >
                      Add shipment
                    </button>
                    <button
                      onClick={() => setShowShipmentForm(false)}
                      className={cn(
                        'flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold transition',
                        !showShipmentForm
                          ? 'bg-black text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-100',
                      )}
                    >
                      Current shipments
                    </button>
                  </div>
                </div>

                {showShipmentForm ? (
                  <>
                    {/* Add shipment form */}
                    <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
                      <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
                        <Sparkles className="h-3.5 w-3.5 text-slate-700" />
                        New dispatch
                      </div>
                      <h2 className="mt-3 text-xl font-semibold tracking-tight">Add shipment</h2>
                      <p className="mt-1.5 text-sm text-muted-foreground">
                        Hub-to-hub dispatch with auto courier assignment.
                      </p>
                    </div>

                    <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
                      <div className="space-y-3">
                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <CitySelect
                            label="City"
                            value={shipmentCityName}
                            onChange={handleShipmentCityChange}
                            cities={shipmentCities}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <HubSelect
                            label="From hub"
                            value={fromHubName}
                            onChange={handleFromHubChange}
                            hubs={shipmentHubs}
                            disabled={!shipmentCityName || shipmentHubsLoading}
                            placeholder={shipmentCityName ? 'Select source hub' : 'Select city first'}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <HubSelect
                            label="To hub"
                            value={toHubName}
                            onChange={setToHubName}
                            hubs={shipmentHubs.filter((h) => h.hub_name !== fromHubName)}
                            disabled={!shipmentCityName || shipmentHubsLoading || !fromHubName}
                            placeholder={fromHubName ? 'Select destination hub' : 'Select source hub first'}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Delivery date
                          </Label>
                          <div className="relative mt-2">
                            <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                              type="date"
                              value={deliveryDate}
                              onChange={(e) => setDeliveryDate(e.target.value)}
                              className="rounded-lg border-border bg-white pl-10 text-sm"
                            />
                          </div>
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Receipt time
                          </Label>
                          <Input
                            type="time"
                            step={1}
                            value={receiptTime}
                            onChange={(e) => setReceiptTime(e.target.value)}
                            className="mt-2 rounded-lg border-border bg-white text-sm"
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Notes
                          </Label>
                          <Textarea
                            placeholder="Optional notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="mt-2 min-h-[72px] rounded-lg border-border bg-white text-sm"
                          />
                        </div>

                        {error && (
                          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                            {error}
                          </div>
                        )}

                        {success && (
                          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                            <p className="font-semibold">Shipment created</p>
                            <p className="mt-1 text-xs">Order: {success.orderId}</p>
                            {success.courierName && (
                              <p className="text-xs">
                                Courier: {success.courierName}
                                {success.courierId ? ` (${success.courierId})` : ''}
                              </p>
                            )}
                            {success.courierHub && (
                              <p className="text-xs">Hub: {success.courierHub}</p>
                            )}
                          </div>
                        )}

                        <Button
                          type="button"
                          disabled={submitting}
                          onClick={handleCreateShipment}
                          className="flex w-full items-center rounded-xl bg-slate-950 px-4 py-3.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
                        >
                          {submitting ? (
                            <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" />
                          ) : (
                            <Plus className="mr-2 h-4 w-4 shrink-0" />
                          )}
                          Create shipment
                          <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
                        </Button>

                        <p className="text-center text-xs text-muted-foreground">
                          Auto-assigns courier based on proximity and hub availability.
                        </p>
                      </div>
                    </div>

                    {/* Dispatch checklist */}
                    <div className="shrink-0 border-t border-border bg-slate-50/60 px-5 py-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                        Dispatch checklist
                      </p>
                      <ul className="mt-3 space-y-2">
                        {dispatchChecklist.map((item) => (
                          <li key={item} className="flex items-start gap-2 text-xs text-muted-foreground">
                            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </>
                ) : (
                  // Manager viewing current shipments
                  shipmentsPanel
                )}
              </>
            )}
          </aside>

          {/* CENTER */}
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
              {[
                { label: 'Live shipments', value: '142' },
                { label: 'Risk events', value: '28' },
                { label: 'AI suggestions', value: '3' },
              ].map((stat, index) => (
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
                    Plotting courier route…
                  </span>
                </div>
              )}
              <RouteMap
                selectedRouteId={selectedRouteId}
                onRouteSelect={handleRouteSelect}
                activeCourierRoute={routeResult}
                highlightedOrderId={highlightedOrderId}
                onStopSelect={setHighlightedOrderId}
                showDemoRoutes={!routeResult}
              />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6">
            {/* Copilot (managers only) */}
            {isManager && (
              <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <ShieldCheck className="h-5 w-5 text-sky-600" />
                  <div>
                    <p className="text-sm font-semibold text-foreground">Logistics Copilot</p>
                    <p className="text-xs text-muted-foreground">
                      Open the AI dispatch assistant in a dedicated view.
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
                        Ask about route planning, delays, courier assignment, and shipment
                        prioritization.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="h-[640px]">
                      <AICopilot />
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            )}

            {/* Route operations */}
            <div className="page-card flex min-h-0 flex-col overflow-hidden p-0">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Live logistics
                </p>
                <h2 className="text-base font-semibold">Route operations</h2>
              </div>

              <div className="grid shrink-0 grid-cols-2 gap-2 border-b border-border p-3">
                {[
                  { label: 'Active routes', value: '142' },
                  { label: 'Delay risk', value: '21%' },
                  { label: 'Critical alerts', value: '7' },
                  { label: 'Hub coverage', value: '18' },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-lg border border-border bg-slate-50/80 p-3">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-1 text-lg font-semibold">{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto custom-scrollbar p-3">
                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">21 routes delayed</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Most impacted: Bengaluru → Chennai.
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">12 recovery actions active</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Priority reallocation in progress.
                  </p>
                </div>
                <div className="rounded-lg border border-amber-100 bg-amber-50/80 p-3 text-sm text-amber-950">
                  Customs hold on RT-3122 may delay arrival by 5 hours.
                </div>
                <div className="rounded-lg border border-red-100 bg-red-50/80 p-3 text-sm text-red-950">
                  Temperature variance detected for Pharma load RT-2978.
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* ── Order detail dialog (managers only) ─────────────────────────── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Shipment details</DialogTitle>
            <DialogDescription>Order and assigned courier information.</DialogDescription>
          </DialogHeader>

          {detailLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading order details…
            </div>
          )}

          {detailError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {detailError}
            </div>
          )}

          {orderDetail && !detailLoading && (
            <div className="space-y-4 text-sm">
              <div className="rounded-xl border border-border bg-slate-50 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Order
                </p>
                <p className="mt-2 font-semibold">{orderDetail.order_id}</p>
                <p className="mt-1 text-muted-foreground">
                  {orderDetail.from_hub_name ?? '—'} → {orderDetail.to_hub_name ?? '—'}
                </p>
                {orderDetail.city_name && (
                  <p className="mt-1 text-muted-foreground">City: {orderDetail.city_name}</p>
                )}
                {orderDetail.delivery_day && (
                  <p className="mt-1 text-muted-foreground">Delivery: {orderDetail.delivery_day}</p>
                )}
                {orderDetail.receipt_time && (
                  <p className="mt-1 text-muted-foreground">Receipt: {orderDetail.receipt_time}</p>
                )}
                {orderDetail.notes && (
                  <p className="mt-2 text-muted-foreground">Notes: {orderDetail.notes}</p>
                )}
              </div>

              <div className="rounded-xl border border-border bg-slate-50 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Assigned courier
                </p>
                {orderDetail.assigned_courier_id ? (
                  <>
                    <p className="mt-2 font-semibold">
                      {orderDetail.assigned_courier_name ?? orderDetail.assigned_courier_id}
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      ID: {orderDetail.assigned_courier_id}
                    </p>
                    {orderDetail.assigned_courier_hub_name && (
                      <p className="mt-1 text-muted-foreground">
                        Hub: {orderDetail.assigned_courier_hub_name}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-2 text-muted-foreground">No courier assigned.</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ── Route dialog ─────────────────────────────────────────────────── */}
      <Dialog open={routeOpen} onOpenChange={setRouteOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {routeResult
                ? `Route for ${routeResult.courier_name ?? routeResult.courier_id}`
                : 'Delivery route'}
            </DialogTitle>
            <DialogDescription>
              {routeResult ? (
                <>
                  {routeResult.delivery_day} · Starting {formatRouteStartTime(routeResult.route_start_time)} ·{' '}
                  {routeResult.total_eta_minutes} min total
                  {routeResult.source === 'graphdb' && (
                    <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      Saved route
                    </span>
                  )}
                  {routeResult.source === 'ml_model' && (
                    <span className="ml-2 rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-800">
                      Predicted now
                    </span>
                  )}
                </>
              ) : (
                'Delivery sequence with ETA for each stop.'
              )}
            </DialogDescription>
          </DialogHeader>

          {routeLoading && (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading route…
            </div>
          )}

          {routeError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {routeError}
            </div>
          )}

          {routeResult && !routeLoading && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    <th className="pb-2 pr-4">#</th>
                    <th className="pb-2 pr-4">Order</th>
                    <th className="pb-2 pr-4">Route</th>
                    <th className="pb-2 pr-4">Leg ETA</th>
                    <th className="pb-2 pr-4">From start</th>
                    <th className="pb-2">Est. arrival</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {routeResult.stops.map((stop) => (
                    <tr key={stop.order_id} className="text-sm">
                      <td className="py-2.5 pr-4 font-semibold text-muted-foreground">
                        {stop.sequence}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{stop.order_id}</td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {stop.from_hub_name ?? '—'} → {stop.to_hub_name ?? '—'}
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                          {stop.eta_minutes} min
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        +{stop.eta_from_start_minutes} min
                      </td>
                      <td className="py-2.5 font-medium">{stop.estimated_arrival}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border">
                    <td colSpan={3} className="pt-3 text-xs text-muted-foreground">
                      Total estimated time
                    </td>
                    <td colSpan={3} className="pt-3 text-right font-semibold">
                      {routeResult.total_eta_minutes} min
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
