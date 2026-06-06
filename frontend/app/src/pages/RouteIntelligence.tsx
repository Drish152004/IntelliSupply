import { useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import { routes } from '@/data/mockData';
import { MapPin, Truck, Clock, AlertTriangle, Sparkles, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function RouteIntelligence() {
  const [selectedRouteId, setSelectedRouteId] = useState<string>(routes[0]?.id ?? '');
  const selectedRoute = useMemo(
    () => routes.find((route) => route.id === selectedRouteId) || routes[0],
    [selectedRouteId],
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-8">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Route intelligence</p>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">High-confidence route planning</h1>
            <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
              Select a route to explore congestion risk, optimization opportunities, and alternate path recommendations.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button className="rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-slate-900">Run scenario model</Button>
            <Button variant="outline" className="rounded-full px-4 py-2 text-sm font-medium">Export route plan</Button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.9fr]">
          <div className="rounded-[2rem] border border-border bg-white shadow-sm overflow-hidden min-h-[720px]">
            <RouteMap selectedRouteId={selectedRouteId} onRouteSelect={setSelectedRouteId} />
          </div>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Selected route</p>
                  <h2 className="mt-2 text-2xl font-semibold text-foreground">{selectedRoute.id}</h2>
                </div>
                <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{selectedRoute.status}</span>
              </div>
              <div className="space-y-4 text-sm text-muted-foreground">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">Origin</p>
                  <p className="mt-1">{selectedRoute.origin.name}</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">Destination</p>
                  <p className="mt-1">{selectedRoute.destination.name}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-6 text-sm">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">ETA</p>
                  <p className="mt-2 font-semibold text-foreground">{selectedRoute.eta}</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Delay risk</p>
                  <p className="mt-2 font-semibold text-foreground">{selectedRoute.delayRisk}%</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Cargo</p>
                  <p className="mt-2 font-semibold text-foreground">{selectedRoute.cargoType}</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Vehicle</p>
                  <p className="mt-2 font-semibold text-foreground">{selectedRoute.vehicleType}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <Sparkles className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Optimization suggestions</p>
                  <p className="text-xs text-muted-foreground">AI-based actions for the selected route.</p>
                </div>
              </div>
              <ol className="space-y-4 text-sm">
                <li className="rounded-3xl border border-border bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">Shift departure window</p>
                  <p className="mt-2 text-muted-foreground">Depart 90 minutes earlier to avoid peak corridor delays and improve ETA confidence.</p>
                </li>
                <li className="rounded-3xl border border-border bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">Reserve alternate hub</p>
                  <p className="mt-2 text-muted-foreground">Use Nagpur transit hub as an alternate buffer for route disruptions.</p>
                </li>
                <li className="rounded-3xl border border-border bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">Reduce load variance</p>
                  <p className="mt-2 text-muted-foreground">Split shipments into two batches to minimize critical delay exposure.</p>
                </li>
              </ol>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Risk factors</p>
                  <p className="text-xs text-muted-foreground">Top operational signals for current route.</p>
                </div>
              </div>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-center gap-3 rounded-3xl bg-slate-50 p-4">
                  <Truck className="h-4 w-4 text-black" />
                  <span>Driver reliability: high</span>
                </div>
                <div className="flex items-center gap-3 rounded-3xl bg-slate-50 p-4">
                  <Clock className="h-4 w-4 text-black" />
                  <span>Traffic window: moderate</span>
                </div>
                <div className="flex items-center gap-3 rounded-3xl bg-slate-50 p-4">
                  <AlertTriangle className="h-4 w-4 text-black" />
                  <span>Weather sensitivity: elevated</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
