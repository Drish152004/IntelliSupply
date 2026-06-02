import { useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import {
  Plus,
  MapPin,
  Truck,
  Sparkles,
  ArrowRight,
  Calendar,
  Boxes,
  Maximize2,
  Minimize2,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';

const dispatchChecklist = [
  'Verify cargo documentation',
  'Confirm hub slot availability',
  'Assign driver and vehicle',
];

export default function LogisticsDashboard() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [copilotExpanded, setCopilotExpanded] = useState(false);
  const [copilotFullscreen, setCopilotFullscreen] = useState(false);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1700px] flex-col px-6 sm:px-8 lg:px-12 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Operations
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Logistics command center
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Create shipments, monitor routes on the live map, and resolve delays with AI-assisted dispatch.
          </p>
        </header>

        <div
          className={cn(
            'grid min-h-0 flex-1 gap-6',
            'h-[calc(100dvh-11.5rem)] min-h-[640px] max-h-[920px]',
            'grid-cols-1 xl:grid-cols-[minmax(272px,280px)_minmax(0,1fr)_minmax(300px,340px)]',
          )}
        >
          {/* Left — Add shipment */}
          <aside className="page-card flex min-h-0 flex-col overflow-hidden">
            <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
              <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
                <Sparkles className="h-3.5 w-3.5 text-slate-700" />
                New dispatch
              </div>
              <h2 className="mt-3 text-xl font-semibold tracking-tight">Add shipment</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Origin, cargo, and priority in one flow.
              </p>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
              <div className="space-y-3">
                <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                  <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    Origin hub
                  </Label>
                  <div className="relative mt-2">
                    <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input placeholder="e.g. Bengaluru WH" className="rounded-lg border-border bg-white pl-10 text-sm" />
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                  <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    Destination
                  </Label>
                  <div className="relative mt-2">
                    <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input placeholder="e.g. Chennai DC" className="rounded-lg border-border bg-white pl-10 text-sm" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-border bg-slate-50/80 p-3">
                    <Label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Cargo</Label>
                    <div className="mt-2 flex items-center gap-2 text-sm font-medium">
                      <Boxes className="h-4 w-4 text-slate-600" />
                      Pharma
                    </div>
                  </div>
                  <div className="rounded-xl border border-border bg-slate-50/80 p-3">
                    <Label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Vehicle</Label>
                    <div className="mt-2 flex items-center gap-2 text-sm font-medium">
                      <Truck className="h-4 w-4 text-slate-600" />
                      Reefer
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                  <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    Departure window
                  </Label>
                  <div className="relative mt-2">
                    <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input type="date" className="rounded-lg border-border bg-white pl-10 text-sm" />
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {['Standard', 'Priority', 'Critical'].map((tier) => (
                    <button
                      key={tier}
                      type="button"
                      className={cn(
                        'rounded-full px-3 py-1.5 text-xs font-semibold transition',
                        tier === 'Priority'
                          ? 'bg-slate-950 text-white'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
                      )}
                    >
                      {tier}
                    </button>
                  ))}
                </div>

                <Button className="flex w-full items-center rounded-xl bg-slate-950 px-4 py-3.5 text-sm font-semibold text-white hover:bg-slate-800">
                  <Plus className="mr-2 h-4 w-4 shrink-0" />
                  Create shipment
                  <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
                </Button>
                <p className="text-center text-xs text-muted-foreground">
                  Auto-assigns route ID and syncs to the live map.
                </p>
              </div>
            </div>

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
          </aside>

          {/* Center — Map */}
          <section className="page-card flex min-h-0 flex-col overflow-hidden p-5">
            <div className="shrink-0 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Map-first operations</p>
                <h2 className="mt-1 text-xl font-semibold sm:text-2xl">Operational map</h2>
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
                  <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{stat.label}</p>
                  <p className="mt-1.5 text-xl font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>

            <div className="relative z-0 isolate mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-border bg-white">
              <RouteMap selectedRouteId={selectedRouteId} onRouteSelect={handleRouteSelect} />
            </div>
          </section>

          {/* Right — Copilot + route operations */}
          <aside className="page-card flex min-h-0 flex-col overflow-hidden p-0">
            <div
              className={cn(
                'flex min-h-0 flex-col border-b border-border',
                copilotExpanded ? 'min-h-[52%]' : 'h-[42%] max-h-[380px] min-h-[280px]',
              )}
            >
              <div className="flex shrink-0 items-start justify-between gap-2 border-b border-border px-4 py-3">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">AI copilot</p>
                  <h2 className="text-base font-semibold">Dispatch assistant</h2>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 rounded-full px-2 text-[11px]"
                    onClick={() => setCopilotExpanded((prev) => !prev)}
                  >
                    {copilotExpanded ? (
                      <>
                        <Minimize2 className="mr-1 h-3 w-3" />
                        Shrink
                      </>
                    ) : (
                      <>
                        <Maximize2 className="mr-1 h-3 w-3" />
                        Expand
                      </>
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 rounded-full px-2 text-[11px]"
                    onClick={() => setCopilotFullscreen(true)}
                  >
                    <ExternalLink className="mr-1 h-3 w-3" />
                    Full
                  </Button>
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-hidden bg-slate-50/40">
                <AICopilot compact expanded={copilotExpanded} />
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">Live logistics</p>
                <h2 className="text-base font-semibold">Route operations</h2>
              </div>

              <div className="grid shrink-0 grid-cols-2 gap-2 border-b border-border p-3">
                {[
                  { label: 'Active routes', value: '142' },
                  { label: 'Delay risk', value: '21%' },
                  { label: 'Critical alerts', value: '7' },
                  { label: 'Hub coverage', value: '18' },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-lg border border-border bg-slate-50/80 p-2.5">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">{stat.label}</p>
                    <p className="mt-1 text-lg font-semibold">{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto custom-scrollbar p-3">
                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">21 routes delayed</p>
                  <p className="mt-1 text-xs text-muted-foreground">Most impacted: Bengaluru → Chennai.</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-semibold">12 recovery actions active</p>
                  <p className="mt-1 text-xs text-muted-foreground">Priority reallocation in progress.</p>
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

      <Dialog open={copilotFullscreen} onOpenChange={setCopilotFullscreen}>
        <DialogContent className="z-[1001] max-w-2xl gap-0 overflow-hidden p-0 sm:max-w-[720px]">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle>Dispatch assistant</DialogTitle>
            <DialogDescription>
              Full-size AI copilot for route planning, delay recovery, and shipment prioritization.
            </DialogDescription>
          </DialogHeader>
          <div className="h-[min(70vh,640px)]">
            <AICopilot />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
