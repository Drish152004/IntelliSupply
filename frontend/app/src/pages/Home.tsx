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
import {
  createShipment,
  getShipment,
  listShipments,
  type OrderDetail,
  type ShipmentListItem,
} from '@/lib/api';
import {
  Plus,
  MapPin,
  Sparkles,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Truck,
  ShieldCheck,
} from 'lucide-react';

const dispatchChecklist = [
  'Verify cargo documentation',
  'Confirm hub slot availability',
  'Assign driver and vehicle',
];

export default function LogisticsDashboard() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  const [showShipmentForm, setShowShipmentForm] = useState(true);

  const [fromHubName, setFromHubName] = useState('');
  const [toHubName, setToHubName] = useState('');
  const [deliveryDate, setDeliveryDate] = useState('');
  const [receiptTime, setReceiptTime] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [success, setSuccess] = useState<{
    orderId: string;
    courierId?: string;
    sequence?: string[];
    routeError?: string | null;
  } | null>(null);
  const [currentShipments, setCurrentShipments] = useState<ShipmentListItem[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    void listShipments()
      .then(setCurrentShipments)
      .catch(() => setCurrentShipments([]));
  }, []);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  const handleViewDetails = async (orderId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setOrderDetail(null);

    try {
      const order = await getShipment(orderId);
      setOrderDetail(order);
    } catch (err) {
      setDetailError(
        err instanceof Error ? err.message : 'Failed to load order details.',
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreateShipment = async () => {
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      let receiptTimeFormatted: string | undefined;

      if (receiptTime) {
        receiptTimeFormatted =
          receiptTime.length === 5
            ? `${receiptTime}:00`
            : receiptTime;
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
        sequence: result.route_prediction?.predicted_sequence,
        routeError: result.route_error,
      });
      void listShipments().then(setCurrentShipments).catch(() => undefined);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to create shipment.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1750px] flex-col px-5 sm:px-7 lg:px-10 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Operations
          </p>

          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Logistics command center
          </h1>

          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Create shipments, monitor routes on the live map,
            and resolve delays with AI-assisted dispatch.
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
            {/* TOGGLE */}
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
                {/* HEADER */}
                <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
                  <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
                    <Sparkles className="h-3.5 w-3.5 text-slate-700" />
                    New dispatch
                  </div>

                  <h2 className="mt-3 text-xl font-semibold tracking-tight">
                    Add shipment
                  </h2>

                  <p className="mt-1.5 text-sm text-muted-foreground">
                    Hub-to-hub dispatch with auto courier assignment.
                  </p>
                </div>

                {/* FORM */}
                <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
                  <div className="space-y-3">
                    <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                      <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                        From hub
                      </Label>

                      <div className="relative mt-2">
                        <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                        <Input
                          placeholder="e.g. Hub_1"
                          value={fromHubName}
                          onChange={(e) =>
                            setFromHubName(e.target.value)
                          }
                          className="rounded-lg border-border bg-white pl-10 text-sm"
                        />
                      </div>
                    </div>

                    <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                      <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                        To hub
                      </Label>

                      <div className="relative mt-2">
                        <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                        <Input
                          placeholder="e.g. Hub_5"
                          value={toHubName}
                          onChange={(e) =>
                            setToHubName(e.target.value)
                          }
                          className="rounded-lg border-border bg-white pl-10 text-sm"
                        />
                      </div>
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
                          onChange={(e) =>
                            setDeliveryDate(e.target.value)
                          }
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
                        <p className="font-semibold">
                          Shipment created
                        </p>

                        <p className="mt-1 text-xs">
                          Order: {success.orderId}
                        </p>

                        {success.courierId && (
                          <p className="text-xs">
                            Courier: {success.courierId}
                          </p>
                        )}

                        {success.sequence &&
                          success.sequence.length > 0 && (
                            <p className="mt-1 text-xs">
                              Route:{' '}
                              {success.sequence.join(' → ')}
                            </p>
                          )}

                        {success.routeError && (
                          <p className="mt-1 text-xs text-amber-800">
                            Route note: {success.routeError}
                          </p>
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
                      Auto-assigns nearest courier and predicts
                      delivery sequence.
                    </p>
                  </div>
                </div>

                {/* CHECKLIST */}
                <div className="shrink-0 border-t border-border bg-slate-50/60 px-5 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                    Dispatch checklist
                  </p>

                  <ul className="mt-3 space-y-2">
                    {dispatchChecklist.map((item) => (
                      <li
                        key={item}
                        className="flex items-start gap-2 text-xs text-muted-foreground"
                      >
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div className="border-b border-border px-5 py-5">
                  <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
                    <Truck className="h-3.5 w-3.5" />
                    Active operations
                  </div>

                  <h2 className="mt-3 text-xl font-semibold tracking-tight">
                    Current shipments
                  </h2>

                  <p className="mt-1.5 text-sm text-muted-foreground">
                    Live dispatches across operational hubs.
                  </p>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                  {currentShipments.map((shipment) => (
                    <div
                      key={shipment.order_id}
                      className="rounded-2xl border border-border bg-slate-50 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold">
                            {shipment.order_id}
                          </p>

                          <p className="mt-1 text-sm text-muted-foreground">
                            {shipment.from_hub_name} → {shipment.to_hub_name}
                          </p>
                        </div>

                        <span
                          className={cn(
                            'rounded-full px-3 py-1 text-[11px] font-semibold',
                            'bg-amber-50 text-amber-700',
                          )}
                        >
                          {shipment.status ?? 'In Transit'}
                        </span>
                      </div>

                      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          Courier: {shipment.assigned_courier_name ?? shipment.assigned_courier_id ?? 'Unassigned'}
                        </span>

                        <button
                          type="button"
                          onClick={() => void handleViewDetails(shipment.order_id)}
                          className="font-medium text-slate-900 hover:underline"
                        >
                          View details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>

          {/* CENTER */}
          <section className="page-card flex min-h-0 flex-col overflow-hidden p-5">
            <div className="shrink-0 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                  Map-first operations
                </p>

                <h2 className="mt-1 text-2xl font-semibold">
                  Operational map
                </h2>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="status-chip bg-emerald-50 text-emerald-700">
                  On time
                </span>

                <span className="status-chip bg-amber-50 text-amber-700">
                  Delayed
                </span>

                <span className="status-chip bg-red-50 text-red-700">
                  Critical
                </span>
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
                  className={cn(
                    'px-4 py-3.5',
                    index < 2 && 'border-r border-border',
                  )}
                >
                  <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                    {stat.label}
                  </p>

                  <p className="mt-1.5 text-xl font-semibold">
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>

            <div className="relative z-0 isolate mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-border bg-white">
              <RouteMap
                selectedRouteId={selectedRouteId}
                onRouteSelect={handleRouteSelect}
              />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6">
            {/* COPILOT BUTTON */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />

                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Logistics Copilot
                  </p>

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
                    <DialogTitle>
                      Logistics Copilot
                    </DialogTitle>

                    <DialogDescription>
                      Ask about route planning, delays, courier
                      assignment, and shipment prioritization.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="h-[640px]">
                    <AICopilot />
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* ROUTE OPS */}
            <div className="page-card flex min-h-0 flex-col overflow-hidden p-0">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Live logistics
                </p>

                <h2 className="text-base font-semibold">
                  Route operations
                </h2>
              </div>

              <div className="grid shrink-0 grid-cols-2 gap-2 border-b border-border p-3">
                {[
                  { label: 'Active routes', value: '142' },
                  { label: 'Delay risk', value: '21%' },
                  { label: 'Critical alerts', value: '7' },
                  { label: 'Hub coverage', value: '18' },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-lg border border-border bg-slate-50/80 p-3"
                  >
                    <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                      {stat.label}
                    </p>

                    <p className="mt-1 text-lg font-semibold">
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto custom-scrollbar p-3">
                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">
                    21 routes delayed
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Most impacted: Bengaluru → Chennai.
                  </p>
                </div>

                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">
                    12 recovery actions active
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Priority reallocation in progress.
                  </p>
                </div>

                <div className="rounded-lg border border-amber-100 bg-amber-50/80 p-3 text-sm text-amber-950">
                  Customs hold on RT-3122 may delay arrival by 5
                  hours.
                </div>

                <div className="rounded-lg border border-red-100 bg-red-50/80 p-3 text-sm text-red-950">
                  Temperature variance detected for Pharma load
                  RT-2978.
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Shipment details</DialogTitle>
            <DialogDescription>
              Order and assigned courier information.
            </DialogDescription>
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
                  <p className="mt-1 text-muted-foreground">
                    Delivery: {orderDetail.delivery_day}
                  </p>
                )}
                {orderDetail.receipt_time && (
                  <p className="mt-1 text-muted-foreground">
                    Receipt: {orderDetail.receipt_time}
                  </p>
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
                    {orderDetail.assigned_courier_email && (
                      <p className="mt-1 text-muted-foreground">
                        Email: {orderDetail.assigned_courier_email}
                      </p>
                    )}
                    {orderDetail.nearest_courier_distance_m != null && (
                      <p className="mt-1 text-muted-foreground">
                        Distance at assignment:{' '}
                        {Math.round(orderDetail.nearest_courier_distance_m)} m
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
    </div>
  );
}