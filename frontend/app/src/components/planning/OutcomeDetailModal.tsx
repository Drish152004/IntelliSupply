import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { OutcomeSummary, ScenarioState } from '@/lib/planningTypes';
import { mapDailyLog } from '@/lib/planningTypes';
import TimelineTable from './TimelineTable';

type CaseId = 'best' | 'likely' | 'worst';

interface OutcomeDetailModalProps {
  caseId: CaseId | null;
  outcomes: OutcomeSummary | null;
  scenario: ScenarioState | null;
  onClose: () => void;
}

export default function OutcomeDetailModal({
  caseId,
  outcomes,
  scenario,
  onClose,
}: OutcomeDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'summary' | 'timeline'>('summary');

  if (!caseId || !outcomes || !scenario) return null;

  const world =
    caseId === 'best'
      ? outcomes.best_case_world
      : caseId === 'likely'
        ? outcomes.most_likely_world
        : outcomes.worst_case_world;

  const caseLabel =
    caseId === 'best' ? 'Best Case' : caseId === 'likely' ? 'Most Likely' : 'Worst Case';

  const logEntries = mapDailyLog(world.daily_log);

  return (
    <Dialog open={caseId !== null} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[750px] max-h-[85vh] flex flex-col rounded-[1.5rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            {caseLabel} — Hub {scenario.hub_id} ({scenario.product_id})
          </DialogTitle>
          <DialogDescription>
            Discrete event simulation metrics for world {world.world_id}
          </DialogDescription>
        </DialogHeader>

        <div className="flex border-b border-slate-200">
          {(['summary', 'timeline'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex-1 pb-3 text-sm font-bold capitalize border-b-2 transition ${
                activeTab === tab
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-400'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto py-4">
          {activeTab === 'summary' ? (
            <div className="grid grid-cols-2 gap-4">
              <SummaryField label="world_id" value={String(world.world_id)} />
              <SummaryField label="ending_inventory" value={`${Math.round(world.ending_inventory).toLocaleString()} units`} />
              <SummaryField label="minimum_inventory" value={`${Math.round(world.minimum_inventory).toLocaleString()} units`} />
              <SummaryField label="stockout_occurred" value={world.stockout_occurred ? 'YES' : 'NO'} highlight={world.stockout_occurred} />
              <SummaryField label="stockout_day" value={world.stockout_day != null ? `Day ${world.stockout_day}` : 'N/A'} />
              <SummaryField label="shortage_quantity" value={`${Math.round(world.shortage_quantity).toLocaleString()} units`} />
              <SummaryField label="safety_stock_breached" value={world.safety_stock_breached ? 'YES' : 'NO'} highlight={world.safety_stock_breached} />
              <SummaryField label="days_below_safety_stock" value={String(world.days_below_safety_stock)} />
            </div>
          ) : (
            <TimelineTable logs={logEntries} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SummaryField({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="border-b border-slate-100 pb-2">
      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{label}</p>
      <p className={`text-sm font-semibold mt-1 ${highlight ? 'text-rose-600' : 'text-slate-800'}`}>
        {value}
      </p>
    </div>
  );
}
