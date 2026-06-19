import { useMemo } from 'react';
import type { AutomationPolicy } from '@/lib/planningTypes';

interface PlanningAutomationPanelProps {
  policies: AutomationPolicy[];
  loading: boolean;
  onChange: (policyType: string, patch: Partial<AutomationPolicy>) => void;
  onSave: (policyType: string) => void;
  savingPolicyType: string | null;
  embedded?: boolean;
}

const LABELS: Record<string, string> = {
  inventory_transfer: 'Inventory Transfer',
  safety_stock_change_pct: 'Safety Stock Change %',
  replenishment_order: 'Replenishment Order',
};

const AUTO_APPROVE_LIMIT_UNITS: Record<string, string> = {
  inventory_transfer: 'units',
  safety_stock_change_pct: '%',
  replenishment_order: 'days',
};

export default function PlanningAutomationPanel({
  policies,
  loading,
  onChange,
  onSave,
  savingPolicyType,
  embedded = false,
}: PlanningAutomationPanelProps) {
  const sortedPolicies = useMemo(
    () =>
      [...policies].sort((a, b) => {
        const order = ['inventory_transfer', 'safety_stock_change_pct', 'replenishment_order'];
        return order.indexOf(a.policy_type) - order.indexOf(b.policy_type);
      }),
    [policies],
  );

  const content = loading ? (
    <p className="text-sm text-slate-500">Loading automation policies…</p>
  ) : (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3">Policy</th>
                <th className="px-4 py-3">Enabled</th>
                <th className="px-4 py-3">Auto Execute</th>
                <th className="px-4 py-3">Auto-approve limit</th>
                <th className="px-4 py-3">Min effectiveness (%)</th>
                <th className="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {sortedPolicies.map((policy) => (
                <tr key={policy.policy_type}>
                  <td className="px-4 py-3 font-semibold text-slate-900">
                    {LABELS[policy.policy_type] ?? policy.policy_type}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    <input
                      type="checkbox"
                      checked={policy.enabled}
                      onChange={(event) =>
                        onChange(policy.policy_type, { enabled: event.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    <input
                      type="checkbox"
                      checked={policy.auto_execute}
                      disabled={!policy.enabled}
                      onChange={(event) =>
                        onChange(policy.policy_type, { auto_execute: event.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      step="0.01"
                      min={0}
                      value={policy.threshold_value}
                      onChange={(event) =>
                        onChange(policy.policy_type, {
                          threshold_value: Number(event.target.value || 0),
                        })
                      }
                      className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                    />
                    <p className="mt-1 text-xs text-slate-400">
                      {AUTO_APPROVE_LIMIT_UNITS[policy.policy_type] ?? 'limit'}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      step={1}
                      min={0}
                      max={100}
                      value={Math.round((policy.utility_score_threshold ?? 0.5) * 100)}
                      onChange={(event) =>
                        onChange(policy.policy_type, {
                          utility_score_threshold: Number(event.target.value || 0) / 100,
                        })
                      }
                      className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onSave(policy.policy_type)}
                      disabled={savingPolicyType === policy.policy_type}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                    >
                      {savingPolicyType === policy.policy_type ? 'Saving…' : 'Save'}
                    </button>
                  </td>
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
          Configure auto-approval behavior for generated recommendations.
        </p>
        {content}
      </div>
    );
  }

  return (
    <section className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">Automation Policies</h3>
      <p className="mt-1 text-sm text-slate-500">
        Configure auto-approval behavior for generated recommendations.
      </p>
      <div className="mt-4">{content}</div>
    </section>
  );
}
