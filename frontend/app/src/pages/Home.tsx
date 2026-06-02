import { useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import ShipmentPanel from '@/components/ShipmentPanel';
import AICopilot from '@/components/AICopilot';

export default function LogisticsDashboard() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="mx-auto max-w-[1600px] px-4 sm:px-6 lg:px-8 pb-8">
        <div className="grid gap-6 pt-6 xl:grid-cols-[minmax(280px,20%)_1fr_minmax(260px,20%)]">
          <aside className="page-card flex min-h-[680px] flex-col overflow-hidden">
            <div className="border-b border-border pb-4">
              <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Live logistics</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">Route operations</h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Monitor active shipments, delay risk and route priority from a focused operational panel.
              </p>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl border border-border bg-slate-50 p-3">
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Active routes</p>
                <p className="mt-3 text-2xl font-semibold text-foreground">142</p>
              </div>
              <div className="rounded-3xl border border-border bg-slate-50 p-3">
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Delay risk</p>
                <p className="mt-3 text-2xl font-semibold text-foreground">21%</p>
              </div>
              <div className="rounded-3xl border border-border bg-slate-50 p-3">
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Critical alerts</p>
                <p className="mt-3 text-2xl font-semibold text-foreground">7</p>
              </div>
              <div className="rounded-3xl border border-border bg-slate-50 p-3">
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Hub coverage</p>
                <p className="mt-3 text-2xl font-semibold text-foreground">18</p>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <button className="rounded-full border border-border bg-white px-4 py-2 text-sm font-medium text-foreground hover:bg-slate-50 transition">
                Refresh routing
              </button>
              <button className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 transition">
                Export manifest
              </button>
            </div>
            <div className="mt-6 border-t border-border pt-5">
              <p className="text-sm font-semibold text-foreground mb-3">Dispatch summary</p>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">21 routes delayed</p>
                  <p className="mt-1">Most impacted corridor: Bengaluru → Chennai.</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="font-semibold text-foreground">12 recovery actions active</p>
                  <p className="mt-1">Priority reallocation in progress for critical loads.</p>
                </div>
              </div>
            </div>
            <div className="mt-6 border-t border-border pt-5">
              <p className="text-sm font-semibold text-foreground mb-3">Operational alerts</p>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li className="rounded-3xl bg-amber-50 p-4">Customs hold on RT-3122 may delay arrival by 5 hours.</li>
                <li className="rounded-3xl bg-red-50 p-4">Temperature variance detected for Pharma load RT-2978.</li>
              </ul>
            </div>
            <div className="mt-auto" />
          </aside>

          <section className="page-card relative min-h-[680px] overflow-hidden">
            <div className="absolute inset-0 rounded-[1.5rem] bg-gradient-to-b from-white/80 via-white/40 to-slate-50 pointer-events-none" />
            <div className="relative z-10 flex h-full flex-col">
              <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Map-first operations</p>
                  <h2 className="mt-2 text-3xl font-semibold text-foreground">Operational map</h2>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="status-chip bg-emerald-50 text-emerald-700">On time</span>
                  <span className="status-chip bg-amber-50 text-amber-700">Delayed</span>
                  <span className="status-chip bg-red-50 text-red-700">Critical</span>
                </div>
              </div>
              <div className="mt-4 flex gap-3 overflow-hidden rounded-[1.5rem] border border-border bg-slate-50">
                <div className="flex-1 border-r border-border px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Live shipments</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">142</p>
                </div>
                <div className="flex-1 border-r border-border px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Risk events</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">28</p>
                </div>
                <div className="flex-1 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">AI suggestions</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">3</p>
                </div>
              </div>
              <div className="mt-5 flex-1 min-h-[600px] overflow-hidden rounded-[1.5rem] border border-border bg-white shadow-sm">
                <RouteMap selectedRouteId={selectedRouteId} onRouteSelect={handleRouteSelect} />
              </div>
            </div>
          </section>

          <aside className="page-card flex min-h-[680px] flex-col overflow-hidden">
            <div className="border-b border-border pb-4">
              <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">AI copilot</p>
              <h2 className="mt-2 text-3xl font-semibold text-foreground">Dispatch assistant</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                One contextual recommendation and one follow-up suggestion for faster route recovery.
              </p>
            </div>
            <div className="mt-5 flex-1 overflow-hidden">
              <AICopilot />
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
