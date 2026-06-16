import { CheckCircle2, Sparkles } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { RankedDecision, RecommendationSummary } from '@/lib/planningTypes';
import { formatPercentFraction } from '@/lib/planningTypes';

interface InterventionDetailModalProps {
  decisionId: string | null;
  rankedDecisions: RankedDecision[];
  recommendation: RecommendationSummary | null;
  onClose: () => void;
}

export default function InterventionDetailModal({
  decisionId,
  rankedDecisions,
  recommendation,
  onClose,
}: InterventionDetailModalProps) {
  if (!decisionId) return null;

  const rd = rankedDecisions.find((r) => r.decision.decision_id === decisionId);
  if (!rd) return null;

  const comp = rd.comparison;
  const isRecommended =
    recommendation?.recommended_decision?.decision.decision_id === decisionId;

  return (
    <Dialog open={decisionId !== null} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[750px] max-h-[85vh] overflow-y-auto rounded-[1.5rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            {rd.decision.title}
          </DialogTitle>
          <DialogDescription>
            Rank #{rd.rank} · Score {(rd.score * 100).toFixed(0)}/100 · {rd.decision.decision_type}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/30 p-4">
            <p className="text-sm text-slate-700">{rd.decision.rationale}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Metric label="Stockout prob. change" value={formatPercentFraction(comp.stockout_probability_change)} />
            <Metric label="Shortage reduction" value={Math.round(comp.shortage_reduction).toLocaleString()} />
            <Metric label="Ending inventory change" value={Math.round(comp.ending_inventory_change).toLocaleString()} />
            <Metric label="Days below SS change" value={comp.days_below_safety_stock_change.toFixed(1)} />
          </div>

          {Object.keys(rd.decision.parameters).length > 0 && (
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Parameters</p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(rd.decision.parameters).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-slate-400">{key}</p>
                    <p className="text-sm font-semibold text-slate-800">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {isRecommended && recommendation?.explanation && (
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" />
                Recommended Action
              </h4>
              <p className="mt-2 text-sm text-slate-700">{recommendation.explanation}</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
