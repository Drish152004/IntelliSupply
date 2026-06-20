import { FileText } from 'lucide-react';
import type { LLMExplanation } from '@/lib/planningTypes';

interface ExplainabilityPanelProps {
  explanation: LLMExplanation;
}

function reportParagraphs(report: string): string[] {
  return report
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

export default function ExplainabilityPanel({ explanation }: ExplainabilityPanelProps) {
  if (!explanation.analyst_report) {
    return null;
  }

  const paragraphs = reportParagraphs(explanation.analyst_report);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Analysis Report</h2>
        <p className="text-xs text-slate-500 mt-1">
          Simulation-backed analyst narrative for this planning scenario.
        </p>
      </div>

      <article className="rounded-[1.5rem] border border-slate-200 bg-white shadow-sm overflow-hidden">
        <header className="flex items-center gap-3 border-b border-slate-100 bg-slate-50/60 px-5 py-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-900">Planning analysis</h3>
            <p className="text-xs text-slate-500">
              Generated from simulation outcomes and ranked interventions
            </p>
          </div>
        </header>

        <div className="space-y-4 p-5">
          {paragraphs.map((paragraph, index) => (
            <p
              key={index}
              className="text-sm text-slate-600 leading-relaxed"
            >
              {paragraph}
            </p>
          ))}
        </div>
      </article>
    </div>
  );
}
