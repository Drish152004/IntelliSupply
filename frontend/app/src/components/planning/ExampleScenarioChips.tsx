import { PLANNING_EXAMPLE_SCENARIOS } from '@/lib/planningExamples';
import type { ScenarioPatch } from '@/lib/planningTypes';

interface ExampleScenarioChipsProps {
  activeExampleId: string | null;
  onSelect: (example: (typeof PLANNING_EXAMPLE_SCENARIOS)[number]) => void;
  disabled?: boolean;
}

export default function ExampleScenarioChips({
  activeExampleId,
  onSelect,
  disabled,
}: ExampleScenarioChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {PLANNING_EXAMPLE_SCENARIOS.map((example) => {
        const isActive = activeExampleId === example.id;
        return (
          <button
            key={example.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(example)}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
              isActive
                ? 'border-indigo-600 bg-indigo-600 text-white shadow-sm'
                : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50'
            }`}
          >
            {example.label}
          </button>
        );
      })}
    </div>
  );
}

export type { ScenarioPatch };
