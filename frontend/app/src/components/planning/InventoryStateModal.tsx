import type { ReactNode } from 'react';
import {
  Activity,
  CalendarDays,
  Package,
  ShieldAlert,
  Warehouse,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { ScenarioState } from '@/lib/planningTypes';
import { asBoolFlag, formatPercentValue } from '@/lib/planningTypes';

interface InventoryStateModalProps {
  cardId: string | null;
  scenario: ScenarioState | null;
  onClose: () => void;
}

function FieldGrid({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {items.map((item) => (
        <div key={item.label} className="border-b border-slate-100 pb-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
          <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

export default function InventoryStateModal({
  cardId,
  scenario,
  onClose,
}: InventoryStateModalProps) {
  if (!cardId || !scenario) return null;

  const inv = scenario.inventory;
  const demand = scenario.demand;
  const forecast = scenario.forecast;
  const risk = scenario.risk;
  const event = scenario.event;
  const replen = scenario.replenishment;

  const iconMap: Record<string, ReactNode> = {
    inventory: <Warehouse className="h-5 w-5 text-blue-600" />,
    demand: <Activity className="h-5 w-5 text-emerald-600" />,
    forecast: <Activity className="h-5 w-5 text-cyan-600" />,
    risk: <ShieldAlert className="h-5 w-5 text-rose-600" />,
    event: <CalendarDays className="h-5 w-5 text-purple-600" />,
    replenishment: <Package className="h-5 w-5 text-amber-600" />,
  };

  let fields: Array<{ label: string; value: string }> = [];

  if (cardId === 'inventory') {
    fields = [
      { label: 'current_stock', value: `${inv.current_stock.toLocaleString()} units` },
      { label: 'safety_stock', value: inv.safety_stock.toFixed(1) },
      { label: 'threshold_quantity', value: inv.threshold_quantity.toFixed(1) },
      { label: 'threshold_gap', value: inv.threshold_gap.toFixed(1) },
      { label: 'threshold_status', value: inv.threshold_status },
      { label: 'coverage_days', value: inv.coverage_days.toFixed(1) },
      { label: 'days_of_inventory_remaining', value: inv.days_of_inventory_remaining.toFixed(1) },
      { label: 'velocity_score', value: inv.velocity_score.toFixed(2) },
      { label: 'velocity_label', value: inv.velocity_label },
      { label: 'inventory_status', value: inv.inventory_status },
    ];
  } else if (cardId === 'demand') {
    fields = [
      { label: 'rolling_7_avg_demand', value: demand.rolling_7_avg_demand.toFixed(2) },
      { label: 'rolling_30_avg_demand', value: demand.rolling_30_avg_demand.toFixed(2) },
      { label: 'demand_growth_pct', value: formatPercentValue(demand.demand_growth_pct) },
      { label: 'previous_year_demand', value: demand.previous_year_demand?.toFixed(2) ?? 'N/A' },
      { label: 'yoy_demand_change_pct', value: demand.yoy_demand_change_pct != null ? formatPercentValue(demand.yoy_demand_change_pct) : 'N/A' },
      { label: 'yoy_trend_label', value: demand.yoy_trend_label },
      { label: 'volatility_label', value: demand.volatility_label },
    ];
  } else if (cardId === 'forecast') {
    fields = [
      { label: 'forecast_date', value: forecast.forecast_date },
      { label: 'predicted_demand', value: Math.round(forecast.predicted_demand).toString() },
      { label: 'lower_bound', value: Math.round(forecast.lower_bound).toString() },
      { label: 'upper_bound', value: Math.round(forecast.upper_bound).toString() },
      { label: 'horizon_days', value: String(forecast.forecast_daily.length) },
    ];
  } else if (cardId === 'risk') {
    fields = [
      { label: 'stock_coverage_risk', value: risk.stock_coverage_risk.toFixed(3) },
      { label: 'demand_volatility_risk', value: risk.demand_volatility_risk.toFixed(3) },
      { label: 'seasonality_risk', value: risk.seasonality_risk.toFixed(3) },
      { label: 'replenishment_delay_risk', value: risk.replenishment_delay_risk.toFixed(3) },
      { label: 'composite_risk_score', value: `${risk.composite_risk_score.toFixed(1)} / 100` },
      { label: 'risk_level', value: risk.risk_level },
      { label: 'primary_risk_driver', value: risk.primary_risk_driver },
    ];
  } else if (cardId === 'event') {
    fields = [
      { label: 'promotion', value: asBoolFlag(event.promotion) ? 'Active' : 'Inactive' },
      { label: 'seasonality', value: event.seasonality },
      { label: 'epidemic', value: asBoolFlag(event.epidemic) ? 'Active' : 'Inactive' },
    ];
  } else if (cardId === 'replenishment') {
    fields = [
      { label: 'has_incoming_replenishment', value: replen.has_incoming_replenishment ? 'Yes' : 'No' },
      { label: 'quantity_ordered', value: replen.quantity_ordered?.toString() ?? 'N/A' },
      { label: 'lead_time_days', value: replen.lead_time_days?.toString() ?? 'N/A' },
      { label: 'priority', value: replen.priority ?? 'N/A' },
      { label: 'expected_arrival_date', value: replen.expected_arrival_date ?? 'N/A' },
    ];
  }

  return (
    <Dialog open={cardId !== null} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[750px] max-h-[85vh] overflow-y-auto rounded-[1.5rem]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 capitalize">
            {iconMap[cardId]}
            {cardId} State
          </DialogTitle>
          <DialogDescription>
            Hub {scenario.hub_id} · {scenario.product_id} · {scenario.category}
          </DialogDescription>
        </DialogHeader>
        <FieldGrid items={fields} />
      </DialogContent>
    </Dialog>
  );
}
