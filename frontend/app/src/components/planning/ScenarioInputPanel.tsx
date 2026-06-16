import { Brain } from 'lucide-react';
import ExampleScenarioChips from './ExampleScenarioChips';
import type { PLANNING_EXAMPLE_SCENARIOS } from '@/lib/planningExamples';

interface ScenarioInputPanelProps {
  scenarioQuery: string;
  setScenarioQuery: (value: string) => void;
  activeExampleId: string | null;
  onSelectExample: (example: (typeof PLANNING_EXAMPLE_SCENARIOS)[number]) => void;
  clarificationQuestions: string[];
  onQueryChange: () => void;
  disabled?: boolean;
}

export default function ScenarioInputPanel({
  scenarioQuery,
  setScenarioQuery,
  activeExampleId,
  onSelectExample,
  clarificationQuestions,
  onQueryChange,
  disabled,
}: ScenarioInputPanelProps) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
          <Brain className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-slate-900">Scenario Input</h2>
          <p className="text-xs text-slate-500">
            Describe a what-if scenario or choose an example below.
          </p>
        </div>
      </div>

      <ExampleScenarioChips
        activeExampleId={activeExampleId}
        onSelect={onSelectExample}
        disabled={disabled}
      />

      <textarea
        value={scenarioQuery}
        onChange={(e) => {
          setScenarioQuery(e.target.value);
          onQueryChange();
        }}
        disabled={disabled}
        rows={3}
        placeholder="e.g. What would happen if demand increases by 25% over the next week?"
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
      />

      {clarificationQuestions.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-wider text-amber-800 mb-2">
            Clarification needed
          </p>
          <ul className="space-y-1">
            {clarificationQuestions.map((q) => (
              <li key={q} className="text-sm text-amber-900">{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
