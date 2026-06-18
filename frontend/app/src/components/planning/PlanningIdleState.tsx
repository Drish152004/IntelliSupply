import { Sparkles } from 'lucide-react';

export default function PlanningIdleState() {
  return (
    <div className="rounded-[1.5rem] border border-dashed border-slate-200 bg-white p-10 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
        <Sparkles className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-lg font-bold text-slate-900">No simulation results yet</h3>
      <p className="mt-2 text-sm text-slate-500 max-w-lg mx-auto">
        Select entity scope, then simulate the current operational state or describe a what-if scenario (or pick an example) to see inventory state, outcome discovery, intervention rankings, and explainability output.
      </p>
    </div>
  );
}
