import {
  Activity,
  CalendarDays,
  ChevronRight,
  Package,
  ShieldAlert,
  Warehouse,
} from 'lucide-react';
import type { ScenarioState } from '@/lib/planningTypes';
import { asBoolFlag, formatPercentFraction } from '@/lib/planningTypes';

interface InventoryStatePanelProps {
  scenario: ScenarioState;
  onSelectCard: (card: string) => void;
}

export default function InventoryStatePanel({
  scenario,
  onSelectCard,
}: InventoryStatePanelProps) {
  const cards = [
    {
      id: 'inventory',
      title: 'Inventory',
      icon: Warehouse,
      color: 'blue',
      summary: `Stock: ${scenario.inventory.current_stock.toLocaleString()} | ${scenario.inventory.coverage_days.toFixed(1)} days coverage`,
    },
    {
      id: 'demand',
      title: 'Demand',
      icon: Activity,
      color: 'emerald',
      summary: `7d avg: ${scenario.demand.rolling_7_avg_demand.toFixed(1)} | growth ${formatPercentFraction(scenario.demand.demand_growth_pct)}`,
    },
    {
      id: 'forecast',
      title: 'Forecast',
      icon: Activity,
      color: 'cyan',
      summary: `Predicted: ${Math.round(scenario.forecast.predicted_demand)} | confidence ${(scenario.forecast.confidence_score * 100).toFixed(0)}%`,
    },
    {
      id: 'risk',
      title: 'Risk',
      icon: ShieldAlert,
      color: 'rose',
      summary: `${scenario.risk.risk_level} | score ${scenario.risk.composite_risk_score.toFixed(0)}/100`,
    },
    {
      id: 'event',
      title: 'Event',
      icon: CalendarDays,
      color: 'purple',
      summary: `Promotion: ${asBoolFlag(scenario.event.promotion) ? 'Yes' : 'No'} | ${scenario.event.seasonality}`,
    },
    {
      id: 'replenishment',
      title: 'Replenishment',
      icon: Package,
      color: 'amber',
      summary: scenario.replenishment.has_incoming_replenishment
        ? `PO: ${scenario.replenishment.quantity_ordered ?? 0} units | delay ${scenario.replenishment.actual_delay_days ?? 0}d`
        : 'No incoming replenishment',
    },
  ];

  const colorMap: Record<string, string> = {
    blue: 'hover:border-blue-300 hover:shadow-[0_0_25px_rgba(59,130,246,0.15)]',
    emerald: 'hover:border-emerald-300 hover:shadow-[0_0_25px_rgba(16,185,129,0.15)]',
    cyan: 'hover:border-cyan-300 hover:shadow-[0_0_25px_rgba(6,182,212,0.15)]',
    rose: 'hover:border-rose-300 hover:shadow-[0_0_25px_rgba(239,68,68,0.15)]',
    purple: 'hover:border-purple-300 hover:shadow-[0_0_25px_rgba(139,92,246,0.15)]',
    amber: 'hover:border-amber-300 hover:shadow-[0_0_25px_rgba(245,158,11,0.15)]',
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Inventory State</h2>
        <p className="text-xs text-slate-500 mt-1">
          Scenario state after applying patch — Hub {scenario.hub_id}, {scenario.product_id}, {scenario.planning_window_days}-day window
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => onSelectCard(card.id)}
              className={`flex flex-col p-5 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 ${colorMap[card.color]}`}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 mb-3">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">{card.title}</h3>
              <p className="mt-2 text-xs text-slate-500 line-clamp-2">{card.summary}</p>
              <div className="mt-3 text-xs font-semibold text-indigo-600 flex items-center gap-1">
                View details
                <ChevronRight className="h-3 w-3" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
