interface RunSimulationBarProps {
  canRun: boolean;
  canRunBaseState: boolean;
  loading: boolean;
  onRun: () => void;
  onRunBaseState: () => void;
  scopeReady: boolean;
  scenarioReady: boolean;
  clarificationActive?: boolean;
}

export default function RunSimulationBar({
  canRun,
  canRunBaseState,
  loading,
  onRun,
  onRunBaseState,
  scopeReady,
  scenarioReady,
  clarificationActive = false,
}: RunSimulationBarProps) {
  let hint = 'Complete entity scope and enter a scenario to run simulation.';
  if (scopeReady && !scenarioReady) {
    hint =
      'Add a what-if scenario to run a scenario simulation, or use Simulate Current State to run without changes.';
  } else if (!scopeReady && scenarioReady) {
    hint = 'Complete entity scope before running simulation.';
  } else if (clarificationActive) {
    hint = 'Fill in the clarification fields below, then apply and run the simulation.';
  } else if (canRun) {
    hint = 'Ready to simulate the scenario against Monte Carlo and DES pipelines.';
  } else if (scopeReady) {
    hint = 'Entity scope is ready. Simulate current state or add a what-if scenario.';
  }

  const scenarioButtonLabel = loading
    ? 'Running Simulation…'
    : clarificationActive
      ? 'Apply & Run Simulation'
      : 'Run Simulation';

  const baseStateButtonLabel = loading ? 'Running Simulation…' : 'Simulate Current State';

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-600 max-w-2xl">{hint}</p>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onRunBaseState}
          disabled={!canRunBaseState || loading}
          className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {baseStateButtonLabel}
        </button>
        <button
          type="button"
          onClick={onRun}
          disabled={!canRun || loading}
          className="inline-flex items-center rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {scenarioButtonLabel}
        </button>
      </div>
    </div>
  );
}
