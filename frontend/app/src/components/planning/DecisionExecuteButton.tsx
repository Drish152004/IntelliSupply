import type { ExecutionDecision, ManualExecutionStatus } from '@/lib/planningTypes';
import { isPolicyExecutable } from '@/lib/planningTypes';

interface DecisionExecuteButtonProps {
  decisionId: string;
  policyEvaluation?: ExecutionDecision;
  manualStatus: ManualExecutionStatus;
  autoExecuted?: boolean;
  onExecute: (decisionId: string) => void;
  className?: string;
}

export default function DecisionExecuteButton({
  decisionId,
  policyEvaluation,
  manualStatus,
  autoExecuted = false,
  onExecute,
  className = '',
}: DecisionExecuteButtonProps) {
  if (!isPolicyExecutable(policyEvaluation)) {
    return null;
  }

  if (autoExecuted) {
    return (
      <p className={`text-xs font-semibold text-emerald-700 ${className}`}>
        Applied automatically
      </p>
    );
  }

  if (manualStatus === 'success') {
    return (
      <p className={`text-xs font-semibold text-emerald-700 ${className}`}>
        Executed successfully
      </p>
    );
  }

  if (manualStatus === 'failed') {
    return (
      <p className={`text-xs font-semibold text-rose-700 ${className}`}>
        Execution failed. Try again.
      </p>
    );
  }

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onExecute(decisionId);
      }}
      disabled={manualStatus === 'executing'}
      className={`rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 ${className}`}
    >
      {manualStatus === 'executing' ? 'Executing…' : 'Execute'}
    </button>
  );
}
