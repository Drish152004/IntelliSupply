import { CheckCircle2 } from 'lucide-react';
import type { OutcomeSummary } from '@/lib/planningTypes';
import { formatPercentFraction } from '@/lib/planningTypes';

type CaseId = 'best' | 'likely' | 'worst';

interface OutcomeDiscoveryPanelProps {
  outcomes: OutcomeSummary;
  selectedCase: CaseId | null;
  onSelectCase: (caseId: CaseId) => void;
}

const CASES: Array<{ id: CaseId; label: string; color: string; worldKey: keyof OutcomeSummary }> = [
  { id: 'best', label: 'Best Case', color: 'emerald', worldKey: 'best_case_world' },
  { id: 'likely', label: 'Most Likely', color: 'amber', worldKey: 'most_likely_world' },
  { id: 'worst', label: 'Worst Case', color: 'rose', worldKey: 'worst_case_world' },
];

export default function OutcomeDiscoveryPanel({
  outcomes,
  selectedCase,
  onSelectCase,
}: OutcomeDiscoveryPanelProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Outcome Discovery</h2>
        <p className="text-xs text-slate-500 mt-1">
          Aggregated baseline simulation results across Monte Carlo worlds.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Stockout probability" value={formatPercentFraction(outcomes.stockout_probability)} />
        <MetricCard label="Avg ending inventory" value={Math.round(outcomes.avg_ending_inventory).toLocaleString()} />
        <MetricCard label="Avg shortage" value={Math.round(outcomes.avg_shortage_quantity).toLocaleString()} />
        <MetricCard label="Days below safety stock" value={outcomes.avg_days_below_safety_stock.toFixed(1)} />
      </div>

      {outcomes.signals.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {outcomes.signals.map((signal) => (
            <span
              key={signal}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
            >
              {signal}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CASES.map((c) => {
          const world = outcomes[c.worldKey] as OutcomeSummary['best_case_world'];
          const isActive = selectedCase === c.id;
          const colorClasses =
            c.color === 'emerald'
              ? isActive
                ? 'bg-emerald-500 text-white border-emerald-600'
                : 'bg-emerald-50 text-emerald-900 border-emerald-200 hover:bg-emerald-100/70'
              : c.color === 'amber'
                ? isActive
                  ? 'bg-amber-500 text-white border-amber-600'
                  : 'bg-amber-50 text-amber-900 border-amber-200 hover:bg-amber-100/70'
                : isActive
                  ? 'bg-rose-500 text-white border-rose-600'
                  : 'bg-rose-50 text-rose-900 border-rose-200 hover:bg-rose-100/70';

          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onSelectCase(c.id)}
              className={`flex flex-col p-5 rounded-[1.5rem] border text-left transition ${colorClasses}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider opacity-85">World</span>
                {isActive && <CheckCircle2 className="h-5 w-5" />}
              </div>
              <h3 className="mt-2 text-xl font-bold">{c.label}</h3>
              <p className="mt-2 text-sm opacity-90">
                Ending inventory: {Math.round(world.ending_inventory).toLocaleString()} ·
                Stockout: {world.stockout_occurred ? 'Yes' : 'No'} ·
                Days below SS: {world.days_below_safety_stock}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}
