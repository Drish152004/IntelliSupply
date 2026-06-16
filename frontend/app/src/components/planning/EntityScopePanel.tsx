import type { PlanningContext } from '@/lib/planningTypes';

interface EntityScopePanelProps {
  hubId: string;
  setHubId: (value: string) => void;
  category: string;
  setCategory: (value: string) => void;
  productId: string;
  setProductId: (value: string) => void;
  simulationDate: string;
  setSimulationDate: (value: string) => void;
  planningWindowDays: number;
  setPlanningWindowDays: (value: number) => void;
  hubs: string[];
  categories: string[];
  products: string[];
  dates: string[];
  loading: boolean;
}

export default function EntityScopePanel({
  hubId,
  setHubId,
  category,
  setCategory,
  productId,
  setProductId,
  simulationDate,
  setSimulationDate,
  planningWindowDays,
  setPlanningWindowDays,
  hubs,
  categories,
  products,
  dates,
  loading,
}: EntityScopePanelProps) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-base font-bold text-slate-900">Entity Scope</h2>
        <p className="text-xs text-slate-500 mt-1">
          Select the hub, product, and simulation date for scenario analysis.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1 min-w-[140px] flex-1">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Hub</label>
          <select
            value={hubId}
            onChange={(e) => setHubId(e.target.value)}
            disabled={loading || hubs.length === 0}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select hub</option>
            {hubs.map((hub) => (
              <option key={hub} value={hub}>Hub {hub}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1 min-w-[140px] flex-1">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={loading || !hubId || categories.length === 0}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select category</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1 min-w-[140px] flex-1">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Product</label>
          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            disabled={loading || !category || products.length === 0}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select product</option>
            {products.map((product) => (
              <option key={product} value={product}>{product}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1 min-w-[140px] flex-1">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Simulation Date</label>
          <select
            value={simulationDate}
            onChange={(e) => setSimulationDate(e.target.value)}
            disabled={loading || !productId || dates.length === 0}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select date</option>
            {dates.map((date) => (
              <option key={date} value={date}>{date}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1 min-w-[120px]">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Simulation Days</label>
          <input
            type="number"
            min={1}
            max={30}
            value={planningWindowDays}
            onChange={(e) => {
              const next = Number(e.target.value);
              if (!Number.isNaN(next)) {
                setPlanningWindowDays(Math.min(30, Math.max(1, next)));
              }
            }}
            disabled={loading}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full"
          />
        </div>
      </div>
    </div>
  );
}

export function deriveScopeOptions(
  context: PlanningContext | null,
  hubId: string,
  category: string,
  productId: string,
) {
  if (!context) {
    return { hubs: [], categories: [], products: [], dates: [] };
  }

  const hubs = [
    ...new Set(context.combinations.map((c) => String(c.hub_id))),
  ].sort((a, b) => Number(a) - Number(b));

  const categories = hubId
    ? [
        ...new Set(
          context.combinations
            .filter((c) => String(c.hub_id) === hubId)
            .map((c) => c.category),
        ),
      ].sort()
    : [];

  const products =
    hubId && category
      ? [
          ...new Set(
            context.combinations
              .filter(
                (c) =>
                  String(c.hub_id) === hubId && c.category === category,
              )
              .map((c) => c.product_id),
          ),
        ].sort()
      : [];

  const validCombo =
    hubId &&
    category &&
    productId &&
    context.combinations.some(
      (c) =>
        String(c.hub_id) === hubId &&
        c.category === category &&
        c.product_id === productId,
    );

  const dates = validCombo ? (context.dates ?? []) : [];

  return { hubs, categories, products, dates };
}
