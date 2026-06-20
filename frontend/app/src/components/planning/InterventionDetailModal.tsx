import { useState } from 'react';
import { ArrowDown, ArrowUp, CheckCircle2, Sparkles } from 'lucide-react';
import DecisionExecuteButton from '@/components/planning/DecisionExecuteButton';
import TimelineTable from '@/components/planning/TimelineTable';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type {
  ActionExecutionResult,
  DecisionSimulationResult,
  ExecutionDecision,
  ManualExecutionStatus,
  OutcomeSummary,
  RankedDecision,
  RecommendationSummary,
} from '@/lib/planningTypes';
import {
  computeMetricComparison,
  formatInterventionPreviewSummary,
  formatPercentFraction,
  isPolicyExecutable,
  mapDailyLog,
  wasAutoExecuted,
} from '@/lib/planningTypes';

type CaseId = 'best' | 'likely' | 'worst';

interface InterventionDetailModalProps {
  decisionId: string | null;
  rankedDecisions: RankedDecision[];
  decisionResults?: DecisionSimulationResult[];
  baselineOutcomes?: OutcomeSummary | null;
  recommendation: RecommendationSummary | null;
  onClose: () => void;
  policyEvaluations?: ExecutionDecision[];
  executionResults?: ActionExecutionResult[];
  manualExecutionState?: Record<string, ManualExecutionStatus>;
  onExecuteDecision?: (decisionId: string) => void;
}

export default function InterventionDetailModal({
  decisionId,
  rankedDecisions,
  decisionResults = [],
  baselineOutcomes = null,
  recommendation,
  onClose,
  policyEvaluations = [],
  executionResults = [],
  manualExecutionState = {},
  onExecuteDecision,
}: InterventionDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'summary' | 'timeline'>('summary');
  const [caseId, setCaseId] = useState<CaseId>('likely');

  if (!decisionId) return null;

  const rd = rankedDecisions.find((r) => r.decision.decision_id === decisionId);
  if (!rd) return null;

  const comp = rd.comparison;
  const decisionResult = decisionResults.find(
    (item) => item.decision.decision_id === decisionId,
  );
  const isRecommended =
    recommendation?.recommended_decision?.decision.decision_id === decisionId;
  const policyEvaluation = policyEvaluations.find(
    (item) => item.decision.decision_id === decisionId,
  );

  const postOutcome = decisionResult?.outcome;
  const baselineStockout = baselineOutcomes?.stockout_probability ?? 0;
  const baselineShortage = baselineOutcomes?.avg_shortage_quantity ?? 0;
  const baselineDaysSs = baselineOutcomes?.avg_days_below_safety_stock ?? 0;
  const baselineEndingInv = baselineOutcomes?.avg_ending_inventory ?? 0;

  const postStockout =
    postOutcome?.stockout_probability ??
    baselineStockout + comp.stockout_probability_change;
  const postShortage =
    postOutcome?.avg_shortage_quantity ??
    baselineShortage - comp.shortage_reduction;
  const postDaysSs =
    postOutcome?.avg_days_below_safety_stock ??
    baselineDaysSs + comp.days_below_safety_stock_change;
  const postEndingInv =
    postOutcome?.avg_ending_inventory ??
    baselineEndingInv + comp.ending_inventory_change;

  const world =
    decisionResult && caseId === 'best'
      ? decisionResult.outcome.best_case_world
      : decisionResult && caseId === 'worst'
        ? decisionResult.outcome.worst_case_world
        : decisionResult?.outcome.most_likely_world;

  const logEntries = mapDailyLog(world?.daily_log);

  return (
    <Dialog open={decisionId !== null} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[750px] max-h-[85vh] flex flex-col rounded-[1.5rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            {rd.decision.title}
          </DialogTitle>
          <DialogDescription>
            Rank #{rd.rank} · {formatInterventionPreviewSummary(rd)} · {rd.decision.decision_type}
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
            <div className="space-y-4">
              <div className="rounded-xl border border-indigo-100 bg-indigo-50/30 p-4">
                <p className="text-sm text-slate-700">{rd.decision.rationale}</p>
              </div>

              {baselineOutcomes && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <MetricBeforeAfter
                    label="Stockout Risk"
                    comparison={computeMetricComparison(
                      baselineStockout,
                      postStockout,
                      true,
                      (v) => formatPercentFraction(v),
                    )}
                    lowerIsBetter
                  />
                  <MetricBeforeAfter
                    label="Expected Shortage"
                    comparison={computeMetricComparison(
                      baselineShortage,
                      postShortage,
                      true,
                      (v) => Math.round(v).toLocaleString(),
                    )}
                    lowerIsBetter
                  />
                  <MetricBeforeAfter
                    label="Days Below Safety Stock"
                    comparison={computeMetricComparison(
                      baselineDaysSs,
                      postDaysSs,
                      true,
                      (v) => v.toFixed(1),
                    )}
                    lowerIsBetter
                  />
                  <MetricBeforeAfter
                    label="Ending Inventory"
                    comparison={computeMetricComparison(
                      baselineEndingInv,
                      postEndingInv,
                      false,
                      (v) => Math.round(v).toLocaleString(),
                    )}
                    lowerIsBetter={false}
                  />
                </div>
              )}

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

              {onExecuteDecision && isPolicyExecutable(policyEvaluation) && (
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/50 p-4">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Execution
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      {policyEvaluation?.status === 'APPROVAL_REQUIRED'
                        ? 'This action requires human approval before execution.'
                        : 'This action can be applied from the planning workspace.'}
                    </p>
                  </div>
                  <DecisionExecuteButton
                    decisionId={rd.decision.decision_id}
                    policyEvaluation={policyEvaluation}
                    autoExecuted={wasAutoExecuted(rd.decision.decision_id, executionResults)}
                    manualStatus={manualExecutionState[rd.decision.decision_id] ?? 'idle'}
                    onExecute={onExecuteDecision}
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex gap-2">
                {(
                  [
                    { id: 'best' as const, label: 'Best Case' },
                    { id: 'likely' as const, label: 'Most Likely' },
                    { id: 'worst' as const, label: 'Worst Case' },
                  ] as const
                ).map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setCaseId(option.id)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      caseId === option.id
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {world && (
                <p className="text-xs text-slate-500">
                  Discrete event simulation for world {world.world_id}
                  {decisionResult
                    ? ` · Hub ${decisionResult.scenario.hub_id} (${decisionResult.scenario.product_id})`
                    : ''}
                </p>
              )}
              <TimelineTable logs={logEntries} />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function MetricBeforeAfter({
  label,
  comparison,
  lowerIsBetter,
}: {
  label: string;
  comparison: ReturnType<typeof computeMetricComparison>;
  lowerIsBetter: boolean;
}) {
  const ArrowIcon = lowerIsBetter
    ? comparison.improved
      ? ArrowDown
      : ArrowUp
    : comparison.improved
      ? ArrowUp
      : ArrowDown;

  const changeColor = comparison.unchanged
    ? 'text-slate-500'
    : comparison.improved
      ? 'text-emerald-600'
      : 'text-red-600';

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-slate-800">
          {comparison.before} → {comparison.after}
        </p>
        {!comparison.unchanged && (
          <span className={`inline-flex items-center gap-0.5 text-xs font-bold ${changeColor}`}>
            <ArrowIcon className="h-3.5 w-3.5" />
            {comparison.pctChange}%
          </span>
        )}
      </div>
    </div>
  );
}
