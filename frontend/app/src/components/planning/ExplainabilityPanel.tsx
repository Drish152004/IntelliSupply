import type { LLMExplanation } from '@/lib/planningTypes';

interface ExplainabilityPanelProps {
  explanation: LLMExplanation;
}

const SECTIONS: Array<{ key: keyof LLMExplanation; title: string }> = [
  { key: 'executive_summary', title: 'Executive Summary' },
  { key: 'recommended_action', title: 'Recommended Action' },
  { key: 'baseline_analysis', title: 'Baseline Analysis' },
  { key: 'decision_comparison', title: 'Decision Comparison' },
  { key: 'best_case_analysis', title: 'Best Case' },
  { key: 'most_likely_analysis', title: 'Most Likely Case' },
  { key: 'worst_case_analysis', title: 'Worst Case' },
];

export default function ExplainabilityPanel({ explanation }: ExplainabilityPanelProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Explainability</h2>
        <p className="text-xs text-slate-500 mt-1">
          LLM-generated narrative grounded in simulation outputs.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {SECTIONS.map((section) => {
          const text = explanation[section.key];
          if (!text) return null;
          return (
            <div
              key={section.key}
              className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm"
            >
              <h3 className="text-sm font-bold text-slate-900">{section.title}</h3>
              <p className="mt-3 text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                {text}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
