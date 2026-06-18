import type { ExecutionDecision, ManualExecutionStatus } from '@/lib/planningTypes';

interface DecisionExecuteButtonProps {
  decisionId: string;
  policyEvaluation?: ExecutionDecision;
  manualStatus: ManualExecutionStatus;
  onExecute: (decisionId: string) => void;
  className?: string;
}

export default function DecisionExecuteButton({
  decisionId,
  policyEvaluation,
  manualStatus,
  onExecute,
  className = '',
}: DecisionExecuteButtonProps) {
  if (policyEvaluation?.status !== 'APPROVAL_REQUIRED') {
    return null;
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
