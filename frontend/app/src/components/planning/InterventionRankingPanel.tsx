import {
  Activity,
  CalendarDays,
  ChevronRight,
  Package,
  Star,
  Truck,
} from 'lucide-react';
import { formatUtilityScore, type RankedDecision, type RecommendationSummary } from '@/lib/planningTypes';

interface InterventionRankingPanelProps {
  rankedDecisions: RankedDecision[];
  recommendation: RecommendationSummary;
  selectedDecisionId: string | null;
  onSelectDecision: (decisionId: string) => void;
}

function iconForType(decisionType: string) {
  if (decisionType.includes('transfer')) return Truck;
  if (decisionType.includes('replenishment') || decisionType.includes('expedite')) return CalendarDays;
  if (decisionType.includes('safety_stock')) return ShieldIcon;
  return Package;
}

function ShieldIcon(props: React.SVGProps<SVGSVGElement>) {
  return <Activity {...props} />;
}

export default function InterventionRankingPanel({
  rankedDecisions,
  recommendation,
  selectedDecisionId,
  onSelectDecision,
}: InterventionRankingPanelProps) {
  const recommendedId = recommendation.recommended_decision?.decision.decision_id;

  if (rankedDecisions.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        No interventions were generated for this scenario.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Intervention Ranking</h2>
        <p className="text-xs text-slate-500 mt-1">
          Ranked corrective decisions evaluated against baseline outcomes.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {rankedDecisions.map((rd) => {
          const Icon = iconForType(rd.decision.decision_type);
          const isSelected = selectedDecisionId === rd.decision.decision_id;
          const isRecommended = recommendedId === rd.decision.decision_id;

          return (
            <button
              key={rd.decision.decision_id}
              type="button"
              onClick={() => onSelectDecision(rd.decision.decision_id)}
              className={`flex flex-col p-5 rounded-[1.5rem] border text-left transition ${
                isSelected
                  ? 'ring-2 ring-indigo-500 border-transparent bg-indigo-50/30'
                  : isRecommended
                    ? 'border-emerald-300 bg-emerald-50/40 hover:shadow-md'
                    : 'border-slate-200 bg-white hover:border-indigo-300 hover:shadow-md'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-500">#{rd.rank}</span>
                {isRecommended && (
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
                    <Star className="h-3.5 w-3.5 fill-emerald-500 text-emerald-500" />
                    Recommended
                  </span>
                )}
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 mb-3">
                <Icon className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-900">{rd.decision.title}</h4>
              <p className="mt-2 text-xs text-slate-500 line-clamp-3">{rd.decision.rationale}</p>
              <p className="mt-3 text-xs font-semibold text-indigo-600">
                Effectiveness: {formatUtilityScore(rd)}
              </p>
              <div className="mt-2 text-xs font-semibold text-indigo-600 flex items-center gap-1">
                View comparison
                <ChevronRight className="h-3 w-3" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
