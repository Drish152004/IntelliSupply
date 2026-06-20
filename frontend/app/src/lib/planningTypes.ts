export interface ScenarioPatch {
  inventory?: {
    current_stock_delta?: number | null;
    safety_stock_multiplier?: number | null;
  } | null;
  demand?: {
    demand_multiplier?: number | null;
  } | null;
  event?: {
    promotion?: boolean | null;
    seasonality?: string | null;
    epidemic?: boolean | null;
  } | null;
  replenishment?: {
    lead_time_days_delta?: number | null;
    actual_delay_days_delta?: number | null;
    quantity_ordered_delta?: number | null;
  } | null;
}

export interface PlanningContext {
  hubs: Array<string | number>;
  products: string[];
  categories: string[];
  dates: string[];
  combinations: Array<{
    category: string;
    product_id: string;
    product_display_name: string;
    hub_id: string | number;
  }>;
}

export interface ScenarioUnderstandingResult {
  status: 'complete' | 'needs_clarification';
  patch?: ScenarioPatch | null;
  partial_patch?: ScenarioPatch | null;
  scenario_types?: string[];
  clarification_prompts?: ClarificationPrompt[];
  clarification_questions?: string[];
}

export interface ClarificationPrompt {
  field_id: string;
  question: string;
}

export interface ClarificationSession {
  partialPatch: ScenarioPatch;
  scenarioTypes: string[];
  prompts: ClarificationPrompt[];
  answers: Record<string, string>;
}

export interface SimulationDay {
  day: number;
  starting_inventory: number;
  demand: number;
  replenishment_received: number;
  ending_inventory: number;
  below_safety_stock: boolean;
  stockout_occurred: boolean;
}

export interface DailyLogEntry {
  day: number;
  startingInventory: number;
  demand: number;
  replenishmentReceived: number;
  endingInventory: number;
  stockoutOccurred: boolean;
  belowSafetyStock: boolean;
}

export interface SimulationResult {
  world_id: number;
  ending_inventory: number;
  minimum_inventory: number;
  stockout_occurred: boolean;
  stockout_day: number | null;
  shortage_quantity: number;
  safety_stock_breached: boolean;
  days_below_safety_stock: number;
  daily_log: SimulationDay[];
}

export interface OutcomeSummary {
  stockout_probability: number;
  avg_ending_inventory: number;
  avg_shortage_quantity: number;
  avg_days_below_safety_stock: number;
  best_case_world: SimulationResult;
  most_likely_world: SimulationResult;
  worst_case_world: SimulationResult;
  signals: string[];
}

export interface InventoryState {
  current_stock: number;
  safety_stock: number;
  threshold_quantity: number;
  threshold_gap: number;
  threshold_status: string;
  coverage_days: number;
  days_of_inventory_remaining: number;
  velocity_score: number;
  velocity_label: string;
  inventory_status: string;
}

export interface DemandState {
  rolling_7_avg_demand: number;
  rolling_30_avg_demand: number;
  demand_growth_pct: number;
  previous_year_demand: number | null;
  yoy_demand_change_pct: number | null;
  yoy_trend_label: string;
  demand_cv: number;
  volatility_label: string;
}

export interface ForecastState {
  forecast_date: string;
  predicted_demand: number;
  lower_bound: number;
  upper_bound: number;
  forecast_uncertainty: number;
  confidence_score: number;
  forecast_daily: number[];
}

export interface RiskState {
  stock_coverage_risk: number;
  demand_volatility_risk: number;
  seasonality_risk: number;
  replenishment_delay_risk: number;
  composite_risk_score: number;
  risk_level: string;
  primary_risk_driver: string;
}

export interface EventState {
  promotion: number | boolean;
  seasonality: string;
  epidemic: number | boolean;
}

export interface ReplenishmentState {
  has_incoming_replenishment: boolean;
  quantity_ordered: number | null;
  quantity_received: number | null;
  lead_time_days: number | null;
  actual_delay_days: number | null;
  replenishment_status: string | null;
  priority: string | null;
  expected_arrival_date: string | null;
  actual_arrival_date: string | null;
}

export interface ScenarioState {
  hub_id: string | number;
  product_id: string;
  category: string;
  simulation_date: string;
  planning_window_days: number;
  inventory: InventoryState;
  demand: DemandState;
  forecast: ForecastState;
  risk: RiskState;
  event: EventState;
  replenishment: ReplenishmentState;
  applied_patch?: ScenarioPatch;
}

export interface DecisionComparison {
  stockout_probability_change: number;
  shortage_reduction: number;
  ending_inventory_change: number;
  days_below_safety_stock_change: number;
}

export interface Decision {
  decision_id: string;
  decision_type: string;
  title: string;
  rationale: string;
  parameters: Record<string, unknown>;
}

export interface RankedDecision {
  rank: number;
  decision: Decision;
  comparison: DecisionComparison;
  impact_score: number;
}

export interface RecommendationSummary {
  recommended_decision: RankedDecision | null;
  explanation: string;
}

export interface DecisionSimulationResult {
  decision: Decision;
  scenario: ScenarioState;
  outcome: OutcomeSummary;
}

export interface ExecutionDecision {
  decision: Decision;
  status: 'AUTO_APPROVED' | 'APPROVAL_REQUIRED' | 'DISABLED';
  reason: string;
  policy_type: string;
  threshold_value?: number | null;
  observed_value?: number | null;
}

export interface ActionExecutionResult {
  decision: Decision;
  success: boolean;
  execution_details: Record<string, unknown>;
}

export interface AutomationPolicy {
  policy_type: string;
  enabled: boolean;
  auto_execute: boolean;
  threshold_value: number;
}

export interface ActionAuditLog {
  timestamp: string;
  decision_id: string;
  decision_type: string;
  decision_parameters: Record<string, unknown> | null;
  policy_type: string;
  execution_status: string;
  reason: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
}

export type ManualExecutionStatus = 'idle' | 'executing' | 'success' | 'failed';

export interface ExecutePlanningDecisionPayload {
  decision: Decision;
  scenario: ScenarioState;
}

export interface ExecutePlanningDecisionResult {
  execution_result: ActionExecutionResult;
  audit_log: ActionAuditLog;
}

export interface LLMExplanation {
  analyst_report: string;
}

export interface PlanningSimulationResult {
  scenario_query: string;
  applied_patch: ScenarioPatch;
  scenario: ScenarioState;
  outcomes: OutcomeSummary;
  ranked_decisions: RankedDecision[];
  decision_results?: DecisionSimulationResult[];
  recommendation_summary: RecommendationSummary;
  policy_evaluations?: ExecutionDecision[];
  execution_results?: ActionExecutionResult[];
  llm_explanation: LLMExplanation;
  decisions?: Decision[];
}

export interface EntityScope {
  hub_id: string;
  product_display_name: string;
  category: string;
  simulation_date: string;
}

export interface SimulatePlanningPayload extends EntityScope {
  scenario_query?: string | null;
  patch?: ScenarioPatch | null;
  simulate_base_state?: boolean;
  planning_window_days?: number;
  n_worlds?: number;
  random_seed?: number | null;
  skip_llm?: boolean;
  auto_select_all_decisions?: boolean;
  selected_decision_ids?: string[] | null;
}

export interface UnderstandScenarioPayload extends EntityScope {
  scenario_query: string;
  partial_patch?: ScenarioPatch | null;
  scenario_types?: string[] | null;
  clarification_answers?: Record<string, string> | null;
}

export function mapSimulationDay(day: SimulationDay): DailyLogEntry {
  return {
    day: day.day,
    startingInventory: day.starting_inventory,
    demand: day.demand,
    replenishmentReceived: day.replenishment_received,
    endingInventory: day.ending_inventory,
    stockoutOccurred: day.stockout_occurred,
    belowSafetyStock: day.below_safety_stock,
  };
}

export function mapDailyLog(log: SimulationDay[] | undefined): DailyLogEntry[] {
  return (log ?? []).map(mapSimulationDay);
}

export function asBoolFlag(value: number | boolean | null | undefined): boolean {
  if (typeof value === 'boolean') return value;
  return Number(value) === 1;
}

export function formatPercentFraction(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** Dataset percent fields (e.g. demand_growth_pct) are already stored as percent, not 0–1 fractions. */
export function formatPercentValue(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/** Interventions shown in the UI must have a positive simulated impact. */
export function filterPositiveImpactDecisions(
  rankedDecisions: RankedDecision[],
): RankedDecision[] {
  return rankedDecisions.filter((rd) => rd.impact_score > 0);
}

export function isPolicyExecutable(evaluation?: ExecutionDecision): boolean {
  return evaluation != null && evaluation.status !== 'DISABLED';
}

export function wasAutoExecuted(
  decisionId: string,
  executionResults?: ActionExecutionResult[],
): boolean {
  return (executionResults ?? []).some(
    (result) => result.decision.decision_id === decisionId && result.success,
  );
}

function formatSignedDelta(value: number, unit: string): string {
  if (value === 0) return '';
  const sign = value > 0 ? '−' : '+';
  return `${sign}${Math.abs(value)} ${unit}`;
}

/** One-line outcome summary for intervention detail views. */
export function formatInterventionPreviewSummary(rd: RankedDecision): string {
  const { comparison } = rd;
  const stockoutPts = Math.round(-comparison.stockout_probability_change * 100);
  if (stockoutPts !== 0) {
    const sign = stockoutPts > 0 ? '−' : '+';
    return `${sign}${Math.abs(stockoutPts)} pts stockout risk`;
  }

  const shortageUnits = Math.round(comparison.shortage_reduction);
  if (shortageUnits !== 0) {
    return `${formatSignedDelta(shortageUnits, 'units avg shortage')}`;
  }

  const daysSs = Math.round(-comparison.days_below_safety_stock_change * 10) / 10;
  if (daysSs !== 0) {
    return `${formatSignedDelta(daysSs, 'days below safety stock')}`;
  }

  const endingInv = Math.round(comparison.ending_inventory_change);
  if (endingInv !== 0) {
    const sign = endingInv > 0 ? '+' : '−';
    return `${sign}${Math.abs(endingInv)} units ending inventory`;
  }

  return 'No material change';
}

export interface MetricComparison {
  before: string;
  after: string;
  pctChange: number;
  improved: boolean;
  unchanged: boolean;
}

export function computeMetricComparison(
  baseline: number,
  post: number,
  lowerIsBetter: boolean,
  formatValue: (value: number) => string,
): MetricComparison {
  const unchanged = post === baseline;
  const improved = lowerIsBetter ? post < baseline : post > baseline;

  let pctChange = 0;
  if (!unchanged) {
    if (baseline === 0) {
      pctChange = 100;
    } else {
      const rawChange = lowerIsBetter
        ? ((baseline - post) / Math.abs(baseline)) * 100
        : ((post - baseline) / Math.abs(baseline)) * 100;
      pctChange = Math.abs(rawChange);
    }
  }

  return {
    before: formatValue(baseline),
    after: formatValue(post),
    pctChange: Math.round(pctChange),
    improved,
    unchanged,
  };
}

export function formatPatchLabels(patch: ScenarioPatch | null | undefined): string[] {
  if (!patch) return [];
  const labels: string[] = [];
  if (patch.demand?.demand_multiplier != null) {
    const pct = ((patch.demand.demand_multiplier - 1) * 100).toFixed(0);
    labels.push(`Demand multiplier: ${patch.demand.demand_multiplier} (${pct}% change)`);
  }
  if (patch.inventory?.current_stock_delta != null) {
    labels.push(`Stock delta: ${patch.inventory.current_stock_delta} units`);
  }
  if (patch.inventory?.safety_stock_multiplier != null) {
    labels.push(`Safety stock multiplier: ${patch.inventory.safety_stock_multiplier}`);
  }
  if (patch.event?.promotion != null) {
    labels.push(`Promotion: ${patch.event.promotion ? 'on' : 'off'}`);
  }
  if (patch.event?.epidemic != null) {
    labels.push(`Epidemic: ${patch.event.epidemic ? 'on' : 'off'}`);
  }
  if (patch.event?.seasonality) {
    labels.push(`Seasonality: ${patch.event.seasonality}`);
  }
  if (patch.replenishment?.actual_delay_days_delta != null) {
    labels.push(`Replenishment delay: +${patch.replenishment.actual_delay_days_delta} days`);
  }
  if (patch.replenishment?.lead_time_days_delta != null) {
    labels.push(`Lead time delta: ${patch.replenishment.lead_time_days_delta} days`);
  }
  if (patch.replenishment?.quantity_ordered_delta != null) {
    labels.push(`Order quantity delta: ${patch.replenishment.quantity_ordered_delta}`);
  }
  return labels;
}

export class PlanningClarificationError extends Error {
  questions: string[];

  constructor(questions: string[]) {
    super(questions.join(' '));
    this.name = 'PlanningClarificationError';
    this.questions = questions;
  }
}
