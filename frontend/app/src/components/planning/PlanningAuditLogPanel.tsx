import type { ActionAuditLog } from '@/lib/planningTypes';

interface PlanningAuditLogPanelProps {
  logs: ActionAuditLog[];
  loading: boolean;
  embedded?: boolean;
}

export default function PlanningAuditLogPanel({
  logs,
  loading,
  embedded = false,
}: PlanningAuditLogPanelProps) {
  const content = loading ? (
    <p className="text-sm text-slate-500">Loading audit logs…</p>
  ) : logs.length === 0 ? (
    <p className="text-sm text-slate-500">No audit logs available yet.</p>
  ) : (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Decision ID</th>
                <th className="px-4 py-3">Policy</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {logs.map((log) => (
                <tr key={`${log.timestamp}-${log.decision_id}`}>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{log.decision_id}</td>
                  <td className="px-4 py-3 text-slate-700">{log.policy_type}</td>
                  <td className="px-4 py-3 font-semibold text-slate-900">{log.execution_status}</td>
                  <td className="px-4 py-3 text-slate-600">{log.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
    </div>
  );

  if (embedded) {
    return (
      <div>
        <p className="text-sm text-slate-500 mb-4">
          Every policy decision and execution attempt is recorded here.
        </p>
        {content}
      </div>
    );
  }

  return (
    <section className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">Action Audit Log</h3>
      <p className="mt-1 text-sm text-slate-500">
        Every policy decision and execution attempt is recorded here.
      </p>
      <div className="mt-4">{content}</div>
    </section>
  );
}
