import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Calendar, Loader2, Route } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import {
  listShipments,
  predictCourierRoute,
  type ShipmentListItem,
  type CourierRouteResult,
} from '@/lib/api';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Courier() {
  const { user, loading: authLoading } = useAuth();

  const [shipments, setShipments] = useState<ShipmentListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [deliveryDay, setDeliveryDay] = useState(todayISO());

  const [routeOpen, setRouteOpen] = useState(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeResult, setRouteResult] = useState<CourierRouteResult | null>(null);

  // ✅ Load ONLY courier shipments
  useEffect(() => {
    if (authLoading || !user) return;

    setLoading(true);

    void listShipments({
      limit: 50,
      deliveryDay,
    })
      .then(setShipments)
      .catch(() => setShipments([]))
      .finally(() => setLoading(false));
  }, [authLoading, user, deliveryDay]);

  // ✅ Predict route (same logic from logistics)
  const handlePredictRoute = async () => {
    setRouteOpen(true);
    setRouteLoading(true);
    setRouteResult(null);

    try {
      const result = await predictCourierRoute('me', deliveryDay);
      setRouteResult(result);
    } catch {
      setRouteResult(null);
    } finally {
      setRouteLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 py-6">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold">My Deliveries</h1>
          <p className="text-sm text-muted-foreground mt-1">
            View your assigned shipments and optimize your route.
          </p>
        </header>

        {/* ✅ Filter */}
        <div className="mb-4">
          <div className="relative w-60">
            <Calendar className="absolute left-2 top-2 h-4 w-4 text-gray-500" />
            <Input
              type="date"
              value={deliveryDay}
              onChange={(e) => setDeliveryDay(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        {/* ✅ Shipments list */}
        <div className="space-y-3">
          {loading && (
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="animate-spin h-4 w-4" />
              Loading shipments...
            </div>
          )}

          {!loading && shipments.length === 0 && (
            <p className="text-sm text-gray-500">
              No shipments assigned.
            </p>
          )}

          {!loading &&
            shipments.map((s) => (
              <div
                key={s.order_id}
                className="border rounded-lg p-4 bg-white shadow-sm"
              >
                <p className="font-semibold">{s.order_id}</p>
                <p className="text-sm text-gray-600">
                  {s.from_hub_name} → {s.to_hub_name}
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  Status: {s.status ?? 'In Transit'}
                </p>
              </div>
            ))}
        </div>

        {/* ✅ Route button */}
        <div className="mt-6">
          <Button
            onClick={handlePredictRoute}
            className="flex items-center gap-2 bg-sky-600 text-white"
          >
            <Route className="h-4 w-4" />
            View My Route
          </Button>
        </div>

        {/* ✅ Route result */}
        {routeOpen && (
          <div className="mt-6 border rounded-lg p-4 bg-white">
            {routeLoading && (
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading route...
              </div>
            )}

            {!routeLoading && routeResult && (
              <div>
                <h2 className="font-semibold mb-3">
                  Route ({routeResult.total_eta_minutes} min)
                </h2>

                <ul className="space-y-2">
                  {routeResult.stops.map((stop) => (
                    <li key={stop.order_id} className="text-sm">
                      {stop.sequence}. {stop.from_hub_name} → {stop.to_hub_name} (
                      {stop.eta_minutes} min)
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}