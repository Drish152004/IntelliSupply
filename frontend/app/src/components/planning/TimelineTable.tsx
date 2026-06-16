import type { DailyLogEntry } from '@/lib/planningTypes';

interface TimelineTableProps {
  logs: DailyLogEntry[];
}

export default function TimelineTable({ logs }: TimelineTableProps) {
  if (logs.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-4 text-center">No daily log entries available.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-4 py-3">Day</th>
            <th className="px-4 py-3">Starting Inventory</th>
            <th className="px-4 py-3">Demand</th>
            <th className="px-4 py-3">Replenishment</th>
            <th className="px-4 py-3">Ending Inventory</th>
            <th className="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {logs.map((row) => {
            let statusText = 'Healthy';
            let statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
            let dotColor = 'bg-emerald-500';

            if (row.stockoutOccurred) {
              statusText = 'Stockout';
              statusColor = 'text-rose-700 bg-rose-50 border-rose-200';
              dotColor = 'bg-rose-500';
            } else if (row.belowSafetyStock) {
              statusText = 'Below Safety Stock';
              statusColor = 'text-amber-700 bg-amber-50 border-amber-200';
              dotColor = 'bg-amber-500';
            }

            return (
              <tr key={row.day} className="hover:bg-slate-50/50 transition">
                <td className="px-4 py-3 font-semibold text-slate-900">Day {row.day}</td>
                <td className="px-4 py-3 text-slate-600">{row.startingInventory.toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-600">{row.demand.toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-600">
                  {row.replenishmentReceived > 0 ? (
                    <span className="inline-flex items-center gap-1 text-indigo-700 font-bold bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full text-xs">
                      +{row.replenishmentReceived.toLocaleString()}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="px-4 py-3 font-semibold text-slate-900">{row.endingInventory.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusColor}`}>
                    <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} />
                    {statusText}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
