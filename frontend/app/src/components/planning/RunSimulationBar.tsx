import { Play } from 'lucide-react';

interface RunSimulationBarProps {
  canRun: boolean;
  loading: boolean;
  onRun: () => void;
  scopeReady: boolean;
  scenarioReady: boolean;
}

export default function RunSimulationBar({
  canRun,
  loading,
  onRun,
  scopeReady,
  scenarioReady,
}: RunSimulationBarProps) {
  let hint = 'Complete entity scope and enter a scenario to run simulation.';
  if (scopeReady && !scenarioReady) {
    hint = 'Add a what-if scenario before running simulation.';
  } else if (!scopeReady && scenarioReady) {
    hint = 'Complete entity scope before running simulation.';
  } else if (canRun) {
    hint = 'Ready to simulate the scenario against Monte Carlo and DES pipelines.';
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-600 max-w-2xl">{hint}</p>
      <button
        type="button"
        onClick={onRun}
        disabled={!canRun || loading}
        className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Play className="h-4 w-4" />
        {loading ? 'Running Simulation…' : 'Run Simulation'}
      </button>
    </div>
  );
}
