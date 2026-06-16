import { useState, useEffect, useMemo, useRef } from 'react';
import Navbar from '@/components/Navbar';
import { runPlanningSimulation, getPlanningFixtures } from '@/lib/api';
import type { PlanningFixtures } from '@/lib/api';
import {
    Sparkles,
    Brain,
    Package,
    Activity,
    ArrowUpRight,
    ChevronRight,
    CheckCircle2,
    Truck,
    CalendarDays,
    Warehouse,
    ShieldAlert,
} from 'lucide-react';

import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';

type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

interface Scenario {
    id: number;
    title: string;
    hubId: string;
    productId: string;
    category: string;
    riskLevel: RiskLevel;
    riskScore: number;
    coverageDays: number;
    currentStock: number;
    safetyStock: number;
    forecastDemand: number;
    confidenceScore: number;
    demandGrowth: number;
    primaryRiskDriver: string;
    replenishmentQty: number;
    etaDays: number;
    recommendation: string;
    situation: string;
    analysis: string;
    inventory: {
        current_stock: number;
        coverage_days: number;
        safety_stock: number;
        inventory_status: string;
    };
    demand: {
        demand_growth_pct: number;
    };
    forecast: {
        predicted_demand: number;
        confidence_score: number;
    };
    risk: {
        risk_level: string;
        composite_risk_score: number;
        primary_risk_driver: string;
    };
    event: {
        promotion: boolean;
        seasonality: string;
    };
    replenishment: {
        quantity_ordered: number;
        lead_time_days: number;
        actual_delay_days: number;
    };
}

interface DailyLogEntry {
    day: number;
    startingInventory: number;
    demand: number;
    replenishmentReceived: number;
    endingInventory: number;
    stockoutOccurred: boolean;
    belowSafetyStock: boolean;
}

interface CaseSimulationData {
    world_id: string;
    ending_inventory: number;
    minimum_inventory: number;
    stockout_occurred: boolean;
    stockout_day: number | string;
    shortage_quantity: number;
    safety_stock_breached: boolean;
    days_below_safety_stock: number;
    daily_log: string;
}

// Mock/static scenario logic removed.

// ==========================================
// SUBCOMPONENTS
// ==========================================

interface TopFiltersProps {
    hubFilter: string;
    setHubFilter: (val: string) => void;
    productFilter: string;
    setProductFilter: (val: string) => void;
    categoryFilter: string;
    setCategoryFilter: (val: string) => void;
    dateFilter: string;
    setDateFilter: (val: string) => void;
    planningWindow: number;
    setPlanningWindow: (val: number) => void;
    categoriesList: string[];
    productsList: string[];
    hubsList: string[];
    datesList: string[];
    onRunSimulation: () => void;
    loading: boolean;
    disabled: boolean;
}

export function TopFilters({
    hubFilter,
    setHubFilter,
    productFilter,
    setProductFilter,
    categoryFilter,
    setCategoryFilter,
    dateFilter,
    setDateFilter,
    planningWindow,
    setPlanningWindow,
    categoriesList,
    productsList,
    hubsList,
    datesList,
    onRunSimulation,
    loading,
    disabled,
}: TopFiltersProps) {
    return (
        <div className="flex flex-wrap items-end gap-6 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm animate-fade-in">

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Hub</label>
                <select
                    value={hubFilter}
                    onChange={(e) => setHubFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    {hubsList.map((hub) => (
                        <option key={hub} value={hub}>Hub {hub}</option>
                    ))}
                </select>
            </div>


            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</label>
                <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    {categoriesList.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                    ))}
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Product ID</label>
                <select
                    value={productFilter}
                    onChange={(e) => setProductFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    {productsList.map((prod) => (
                        <option key={prod} value={prod}>{prod}</option>
                    ))}
                </select>
            </div>



            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Simulation Date</label>
                <select
                    value={dateFilter}
                    onChange={(e) => setDateFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    {datesList.map((dt) => (
                        <option key={dt} value={dt}>{dt}</option>
                    ))}
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Planning Window</label>
                <select
                    value={planningWindow}
                    onChange={(e) => setPlanningWindow(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={30}>30 days</option>
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1 justify-end">
                <button
                    onClick={onRunSimulation}
                    disabled={loading || disabled}
                    className="w-full bg-indigo-600 text-white rounded-xl px-4 py-2 text-sm font-semibold hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 h-[38px]"
                >
                    {loading ? (
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                        <Activity className="h-4 w-4" />
                    )}
                    <span>{loading ? 'Running...' : 'Run Simulation'}</span>
                </button>
            </div>
        </div>
    );
}

interface StateCardsProps {
    selectedScenario: Scenario;
    setSelectedStateCard: (card: string) => void;
}

export function StateCards({ selectedScenario, setSelectedStateCard }: StateCardsProps) {
    const scenario = selectedScenario;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-800">Current Scenarios</h2>
                <span className="text-xs font-semibold text-slate-400">Click a card to examine detailed data telemetry</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
                {/* 1. Inventory Card */}
                <button
                    onClick={() => setSelectedStateCard('inventory')}
                    className="flex flex-col p-6 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 hover:shadow-[0_0_25px_rgba(59,130,246,0.15)] hover:border-blue-300 justify-between h-full group"
                >
                    <div>
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 mb-4 transition-colors group-hover:bg-blue-100">
                            <Warehouse className="h-5 w-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Inventory</h3>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
                            Stock: {scenario.inventory.current_stock} | {scenario.inventory.coverage_days} days remaining
                        </p>
                    </div>
                    <div className="mt-4 text-xs font-semibold text-blue-600 flex items-center gap-1">
                        View telemetry details
                        <ChevronRight className="h-3 w-3" />
                    </div>
                </button>

                {/* 2. Demand Card */}
                <button
                    onClick={() => setSelectedStateCard('demand')}
                    className="flex flex-col p-6 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 hover:shadow-[0_0_25px_rgba(16,185,129,0.15)] hover:border-emerald-300 justify-between h-full group"
                >
                    <div>
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 mb-4 transition-colors group-hover:bg-emerald-100">
                            <Activity className="h-5 w-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Demand</h3>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
                            Forecast: {scenario.forecast.predicted_demand} | +{scenario.demand.demand_growth_pct * 100}% growth trend
                        </p>
                    </div>
                    <div className="mt-4 text-xs font-semibold text-emerald-600 flex items-center gap-1">
                        View telemetry details
                        <ChevronRight className="h-3 w-3" />
                    </div>
                </button>

                {/* 3. Risk Card */}
                <button
                    onClick={() => setSelectedStateCard('risk')}
                    className="flex flex-col p-6 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 hover:shadow-[0_0_25px_rgba(239,68,68,0.15)] hover:border-rose-300 justify-between h-full group"
                >
                    <div>
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600 mb-4 transition-colors group-hover:bg-rose-100">
                            <ShieldAlert className="h-5 w-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Risk</h3>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
                            Level: {scenario.risk.risk_level} | Composite score: {scenario.risk.composite_risk_score}/100
                        </p>
                    </div>
                    <div className="mt-4 text-xs font-semibold text-rose-600 flex items-center gap-1">
                        View telemetry details
                        <ChevronRight className="h-3 w-3" />
                    </div>
                </button>

                {/* 4. Event Card */}
                <button
                    onClick={() => setSelectedStateCard('event')}
                    className="flex flex-col p-6 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 hover:shadow-[0_0_25px_rgba(139,92,246,0.15)] hover:border-purple-300 justify-between h-full group"
                >
                    <div>
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600 mb-4 transition-colors group-hover:bg-purple-100">
                            <CalendarDays className="h-5 w-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Event</h3>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
                            Promotion: {scenario.event.promotion ? "Yes" : "No"} | Seasonality: {scenario.event.seasonality}
                        </p>
                    </div>
                    <div className="mt-4 text-xs font-semibold text-purple-600 flex items-center gap-1">
                        View telemetry details
                        <ChevronRight className="h-3 w-3" />
                    </div>
                </button>

                {/* 5. Replenishment Card */}
                <button
                    onClick={() => setSelectedStateCard('replenishment')}
                    className="flex flex-col p-6 rounded-[1.5rem] border border-slate-200 bg-white text-left transition-all duration-300 hover:shadow-[0_0_25px_rgba(245,158,11,0.15)] hover:border-amber-300 justify-between h-full group"
                >
                    <div>
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600 mb-4 transition-colors group-hover:bg-amber-100">
                            <Package className="h-5 w-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Replenishment</h3>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
                            Inbound PO: {scenario.replenishment.quantity_ordered} units | Delay: {scenario.replenishment.actual_delay_days} days
                        </p>
                    </div>
                    <div className="mt-4 text-xs font-semibold text-amber-600 flex items-center gap-1">
                        View telemetry details
                        <ChevronRight className="h-3 w-3" />
                    </div>
                </button>
            </div>
        </div>
    );
}

export function CopilotInput() {
    return (
        <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                    <Brain className="h-5 w-5 animate-pulse" />
                </div>
                <div>
                    <h2 className="text-base font-bold text-slate-900">Planning Copilot</h2>
                    <p className="text-xs text-slate-500">Ask the AI Copilot to execute planning queries or generate simulated rules</p>
                </div>
            </div>

            <div className="flex items-center gap-3">
                <input
                    type="text"
                    placeholder="Ask about inventory, demand, risk, or run a simulation..."
                    className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50 text-slate-800 transition-all"
                />
                <button className="bg-indigo-600 text-white rounded-xl px-5 py-3 text-sm font-semibold hover:bg-indigo-700 transition flex items-center gap-2">
                    <span>Ask Copilot</span>
                    <ArrowUpRight className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}

interface CaseScenarioCardsProps {
    selectedCase: string | null;
    onSelectCase: (caseId: string) => void;
}

export function CaseScenarioCards({ selectedCase, onSelectCase }: CaseScenarioCardsProps) {
    const caseScenarios = [
        {
            id: 'best',
            label: 'Best Case',
            color: 'emerald',
        },
        {
            id: 'likely',
            label: 'Most Likely',
            color: 'amber',
        },
        {
            id: 'worst',
            label: 'Worst Case',
            color: 'rose',
        },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-800">Case Scenarios</h2>
                <span className="text-xs font-semibold text-slate-400">Select a case behavior to reveal simulation logs</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {caseScenarios.map((c) => {
                    const isActive = selectedCase === c.id;
                    let colorClasses = '';
                    if (c.color === 'emerald') {
                        colorClasses = isActive
                            ? 'bg-emerald-500 text-white border-emerald-600 shadow-lg shadow-emerald-100'
                            : 'bg-emerald-50 text-emerald-900 border-emerald-200 hover:bg-emerald-100/70';
                    } else if (c.color === 'amber') {
                        colorClasses = isActive
                            ? 'bg-amber-500 text-white border-amber-600 shadow-lg shadow-amber-100'
                            : 'bg-amber-50 text-amber-900 border-amber-200 hover:bg-amber-100/70';
                    } else {
                        colorClasses = isActive
                            ? 'bg-rose-500 text-white border-rose-600 shadow-lg shadow-rose-100'
                            : 'bg-rose-50 text-rose-900 border-rose-200 hover:bg-rose-100/70';
                    }

                    return (
                        <button
                            key={c.id}
                            onClick={() => onSelectCase(c.id)}
                            className={`flex flex-col p-6 rounded-[1.5rem] border text-left transition-all duration-300 ${colorClasses}`}
                        >
                            <div className="flex items-center justify-between w-full">
                                <span className="text-xs font-semibold uppercase tracking-wider opacity-85">
                                    Simulation Case
                                </span>
                                {isActive && <CheckCircle2 className="h-5 w-5" />}
                            </div>
                            <h3 className="mt-2 text-2xl font-bold">{c.label}</h3>
                            <p className="mt-2 text-sm opacity-80 leading-relaxed">
                                {c.id === 'best' && 'Optimistic assumptions: high supply reliability, stable demand growth, and fast logistics.'}
                                {c.id === 'likely' && 'Baseline projection: standard transit times, average seasonal demand, and minor delay risk.'}
                                {c.id === 'worst' && 'Stress test scenario: severe supplier delays, demand spikes, and logistical congestion.'}
                            </p>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

interface DecisionCardsProps {
    selectedCase: string | null;
    selectedDecision: string | null;
    onSelectDecision: (decision: string) => void;
    decisionsList: any[];
}

export function DecisionCards({ selectedCase, selectedDecision, onSelectDecision, decisionsList }: DecisionCardsProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-800">Select Simulation Decision</h2>
                <span className="text-xs font-semibold text-slate-400">
                    (Impact calculated under {selectedCase ? (selectedCase === 'best' ? 'Best Case' : selectedCase === 'likely' ? 'Most Likely' : 'Worst Case') : 'Most Likely'} scenario)
                </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {decisionsList.map((dec) => {
                    const DecIcon = dec.icon;
                    const isSelected = selectedDecision === dec.name;

                    return (
                        <button
                            key={dec.name}
                            onClick={() => onSelectDecision(dec.name)}
                            className={`flex flex-col p-5 rounded-[1.5rem] border text-left transition-all duration-300 bg-white hover:border-indigo-300 hover:shadow-md
                                ${isSelected ? 'ring-2 ring-indigo-500 border-transparent shadow-sm bg-indigo-50/20' : 'border-slate-200'}
                            `}
                        >
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 mb-4">
                                <DecIcon className="h-5 w-5" />
                            </div>
                            <h4 className="font-bold text-slate-900">{dec.name}</h4>
                            <p className="mt-2 text-xs text-slate-500 leading-relaxed">{dec.desc}</p>
                            <div className="mt-4 text-xs font-semibold text-indigo-600 flex items-center gap-1">
                                Simulate Impact
                                <ChevronRight className="h-3 w-3" />
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

interface TimelineTableProps {
    logs: DailyLogEntry[];
}

export function TimelineTable({ logs }: TimelineTableProps) {
    return (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500">
                    <tr>
                        <th className="px-4 py-3">Day</th>
                        <th className="px-4 py-3">Starting Inventory</th>
                        <th className="px-4 py-3">Demand</th>
                        <th className="px-4 py-3">Replenishment Received</th>
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

interface ScenarioModalProps {
    caseId: string | null;
    onClose: () => void;
    scenario: Scenario;
    simulationData?: any;
}

export function ScenarioModal({ caseId, onClose, scenario, simulationData }: ScenarioModalProps) {
    const [activeTab, setActiveTab] = useState<'summary' | 'timeline'>('summary');

    if (!caseId) return null;

    let simData: any = null;
    let logEntries: DailyLogEntry[] = [];

    if (simulationData?.outcomes) {
        const outcomes = simulationData.outcomes;
        let realWorld: any;
        if (caseId === 'best') realWorld = outcomes.best_case_world;
        else if (caseId === 'likely') realWorld = outcomes.most_likely_world;
        else realWorld = outcomes.worst_case_world;

        if (realWorld) {
            simData = {
                world_id: String(realWorld.world_id),
                ending_inventory: realWorld.ending_inventory,
                minimum_inventory: realWorld.minimum_inventory,
                stockout_occurred: realWorld.stockout_occurred,
                stockout_day: realWorld.stockout_occurred ? (realWorld.stockout_day !== null ? realWorld.stockout_day : 'N/A') : 'N/A',
                shortage_quantity: realWorld.shortage_quantity,
                safety_stock_breached: realWorld.safety_stock_breached,
                days_below_safety_stock: realWorld.days_below_safety_stock,
            };
            logEntries = realWorld.daily_log || [];
        }
    }

    if (!simData) return null;

    const caseLabel = caseId === 'best' ? 'Best Case' : caseId === 'likely' ? 'Most Likely' : 'Worst Case';

    return (
        <Dialog open={caseId !== null} onOpenChange={() => onClose()}>
            <DialogContent className="sm:max-w-[750px] w-full sm:h-[750px] rounded-[1.5rem] border border-slate-200 p-6 overflow-hidden bg-white flex flex-col justify-between">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <DialogHeader className="shrink-0 mb-4">
                        <DialogTitle className="text-xl font-bold text-slate-900 flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-indigo-600 animate-pulse" />
                            {caseLabel} Projections — {scenario.title}
                        </DialogTitle>
                        <DialogDescription className="text-sm text-slate-500 mt-1">
                            Detailed simulation metrics under {caseLabel} conditions.
                        </DialogDescription>
                    </DialogHeader>

                    {/* Tab Switcher */}
                    <div className="flex border-b border-slate-200 mb-6 shrink-0">
                        <button
                            onClick={() => setActiveTab('summary')}
                            className={`flex-1 pb-3 text-sm font-bold text-center border-b-2 transition-all ${activeTab === 'summary'
                                ? 'border-indigo-600 text-indigo-600'
                                : 'border-transparent text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            Summary
                        </button>
                        <button
                            onClick={() => setActiveTab('timeline')}
                            className={`flex-1 pb-3 text-sm font-bold text-center border-b-2 transition-all ${activeTab === 'timeline'
                                ? 'border-indigo-600 text-indigo-600'
                                : 'border-transparent text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            Timeline
                        </button>
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-y-auto pr-2 px-1 py-1">
                        {activeTab === 'summary' ? (
                            <div className="grid grid-cols-2 gap-6">
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">world_id</p>
                                    <p className="text-sm font-semibold text-slate-800 mt-1">{simData.world_id}</p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">ending_inventory</p>
                                    <p className="text-sm font-semibold text-slate-800 mt-1">{simData.ending_inventory.toLocaleString()} units</p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">minimum_inventory</p>
                                    <p className="text-sm font-semibold text-slate-800 mt-1">{simData.minimum_inventory.toLocaleString()} units</p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">stockout_occurred</p>
                                    <p className={`text-sm font-bold mt-1 ${simData.stockout_occurred ? 'text-rose-600 animate-pulse' : 'text-emerald-600'}`}>
                                        {simData.stockout_occurred ? 'YES' : 'NO'}
                                    </p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">stockout_day</p>
                                    <p className={`text-sm font-semibold mt-1 ${simData.stockout_occurred ? 'text-rose-600 font-bold' : 'text-slate-800'}`}>
                                        {simData.stockout_day === 'N/A' ? 'N/A' : `Day ${simData.stockout_day}`}
                                    </p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">shortage_quantity</p>
                                    <p className="text-sm font-semibold text-slate-800 mt-1">{simData.shortage_quantity.toLocaleString()} units</p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">safety_stock_breached</p>
                                    <p className={`text-sm font-bold mt-1 ${simData.safety_stock_breached ? 'text-rose-600' : 'text-emerald-600'}`}>
                                        {simData.safety_stock_breached ? 'YES (CRITICAL)' : 'NO (HEALTHY)'}
                                    </p>
                                </div>
                                <div className="border-b border-slate-100 pb-3">
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">days_below_safety_stock</p>
                                    <p className="text-sm font-semibold text-slate-800 mt-1">{simData.days_below_safety_stock} days</p>
                                </div>
                            </div>
                        ) : (
                            <TimelineTable logs={logEntries} />
                        )}
                    </div>
                </div>

                <div className="mt-6 flex justify-end shrink-0">
                    <button
                        onClick={() => onClose()}
                        className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 transition"
                    >
                        Close Projections
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

interface StateCardDetailsModalProps {
    selectedStateCard: string | null;
    setSelectedStateCard: (card: string | null) => void;
    selectedScenario: Scenario;
}

export function StateCardDetailsModal({
    selectedStateCard,
    setSelectedStateCard,
    selectedScenario,
}: StateCardDetailsModalProps) {
    if (!selectedStateCard) return null;

    return (
        <Dialog
            open={selectedStateCard !== null}
            onOpenChange={() => setSelectedStateCard(null)}
        >
            <DialogContent className="sm:max-w-[750px] w-full sm:h-[750px] rounded-[1.5rem] border border-slate-200 p-6 overflow-hidden bg-white flex flex-col justify-between">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <DialogHeader className="shrink-0 mb-4">
                        <DialogTitle className="text-xl font-bold text-slate-900 flex items-center gap-2">
                            {selectedStateCard === 'inventory' && <Warehouse className="h-5 w-5 text-blue-600" />}
                            {selectedStateCard === 'demand' && <Activity className="h-5 w-5 text-emerald-600" />}
                            {selectedStateCard === 'risk' && <ShieldAlert className="h-5 w-5 text-rose-600" />}
                            {selectedStateCard === 'event' && <CalendarDays className="h-5 w-5 text-purple-600" />}
                            {selectedStateCard === 'replenishment' && <Package className="h-5 w-5 text-amber-600" />}
                            {selectedStateCard.charAt(0).toUpperCase() + selectedStateCard.slice(1)} State Details
                        </DialogTitle>
                        <DialogDescription className="text-sm text-slate-500 mt-1">
                            Detailed telemetry for {selectedScenario.title}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto pr-2">
                        {selectedStateCard === 'inventory' && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'current_stock', value: `${selectedScenario.currentStock.toLocaleString()} units` },
                                    { label: 'safety_stock', value: `${selectedScenario.safetyStock.toLocaleString()} units` },
                                    { label: 'threshold_quantity', value: `${(selectedScenario.safetyStock * 0.8).toLocaleString()} units` },
                                    { label: 'threshold_gap', value: `${(selectedScenario.currentStock - selectedScenario.safetyStock).toLocaleString()} units` },
                                    { label: 'threshold_status', value: selectedScenario.currentStock < selectedScenario.safetyStock ? 'WARNING' : 'HEALTHY' },
                                    { label: 'coverage_days', value: `${selectedScenario.coverageDays} days` },
                                    { label: 'days_of_inventory_remaining', value: `${selectedScenario.coverageDays} days` },
                                    { label: 'velocity_score', value: (selectedScenario.riskScore / 10).toFixed(1) },
                                    { label: 'velocity_label', value: selectedScenario.riskLevel },
                                    { label: 'inventory_status', value: selectedScenario.currentStock < selectedScenario.safetyStock ? 'UNDERSTOCK' : 'HEALTHY' },
                                ].map((item) => (
                                    <div key={item.label} className="border-b border-slate-100 pb-2">
                                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
                                        <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {selectedStateCard === 'demand' && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'rolling_7_avg_demand', value: `${Math.round(selectedScenario.forecastDemand / 30).toLocaleString()} units/day` },
                                    { label: 'rolling_30_avg_demand', value: `${selectedScenario.forecastDemand.toLocaleString()} units/mo` },
                                    { label: 'demand_growth_pct', value: `+${selectedScenario.demandGrowth}%` },
                                    { label: 'previous_year_demand', value: `${Math.round(selectedScenario.forecastDemand * 0.85).toLocaleString()} units/mo` },
                                    { label: 'yoy_demand_change_pct', value: `+${(selectedScenario.demandGrowth * 0.9).toFixed(1)}%` },
                                    { label: 'yoy_trend_label', value: selectedScenario.demandGrowth > 20 ? 'STRONG_GROWTH' : 'STABLE' },
                                    { label: 'demand_cv', value: '0.15' },
                                    { label: 'volatility_label', value: 'MODERATE' },
                                ].map((item) => (
                                    <div key={item.label} className="border-b border-slate-100 pb-2">
                                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
                                        <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {selectedStateCard === 'risk' && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'stock_coverage_risk', value: (selectedScenario.riskScore / 100).toFixed(2) },
                                    { label: 'demand_volatility_risk', value: '0.45' },
                                    { label: 'seasonality_risk', value: selectedScenario.primaryRiskDriver === 'Seasonality' ? '0.85' : '0.20' },
                                    { label: 'replenishment_delay_risk', value: selectedScenario.primaryRiskDriver === 'Inbound Delay' ? '0.80' : '0.15' },
                                    { label: 'composite_risk_score', value: `${selectedScenario.riskScore} / 100` },
                                    { label: 'risk_level', value: selectedScenario.riskLevel },
                                    { label: 'primary_risk_driver', value: selectedScenario.primaryRiskDriver },
                                ].map((item) => (
                                    <div key={item.label} className="border-b border-slate-100 pb-2">
                                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
                                        <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {selectedStateCard === 'event' && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'promotion', value: selectedScenario.primaryRiskDriver === 'Demand Surge' ? 'Mega Promotion Active' : 'None' },
                                    { label: 'seasonality', value: selectedScenario.primaryRiskDriver === 'Seasonality' ? 'High Seasonality Factor' : 'Standard' },
                                    { label: 'epidemic', value: 'None' },
                                ].map((item) => (
                                    <div key={item.label} className="border-b border-slate-100 pb-2">
                                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
                                        <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {selectedStateCard === 'replenishment' && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'has_incoming_replenishment', value: selectedScenario.replenishmentQty > 0 ? 'Yes' : 'No' },
                                    { label: 'quantity_ordered', value: `${selectedScenario.replenishmentQty.toLocaleString()} units` },
                                    { label: 'quantity_received', value: '0 units' },
                                    { label: 'lead_time_days', value: '7 days' },
                                    { label: 'actual_delay_days', value: `${selectedScenario.etaDays} days` },
                                    { label: 'replenishment_status', value: selectedScenario.etaDays > 5 ? 'DELAYED' : 'IN_TRANSIT' },
                                    { label: 'priority', value: selectedScenario.riskLevel },
                                    { label: 'expected_arrival_date', value: '2026-06-18' },
                                    { label: 'actual_arrival_date', value: `2026-06-${18 + selectedScenario.etaDays}` },
                                ].map((item) => (
                                    <div key={item.label} className="border-b border-slate-100 pb-2">
                                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{item.label}</p>
                                        <p className="text-sm font-semibold text-slate-800 mt-0.5">{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="mt-6 flex justify-end shrink-0">
                    <button
                        onClick={() => setSelectedStateCard(null)}
                        className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 transition"
                    >
                        Close Details
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

interface DecisionModalProps {
    selectedDecision: string | null;
    setSelectedDecision: (decision: string | null) => void;
    selectedScenario: Scenario;
    selectedCase: string | null;
    simulationData?: any;
}

export function DecisionModal({
    selectedDecision,
    setSelectedDecision,
    selectedScenario,
    selectedCase,
    simulationData,
}: DecisionModalProps) {
    if (!selectedDecision) return null;

    const matchedRanked = simulationData?.ranked_decisions?.find((rd: any) => rd.decision.title === selectedDecision);

    if (!matchedRanked) return null;

    const comp = matchedRanked.comparison;
    const rd = matchedRanked;

    const summary = rd.decision.rationale;

    const stockoutDelta = Math.round(comp.stockout_probability_change * 100);
    const shortageRed = Math.round(comp.shortage_reduction);
    const endingInvDelta = Math.round(comp.ending_inventory_change);
    const daysBreachDelta = comp.days_below_safety_stock_change.toFixed(1);

    const demandImpact = stockoutDelta < 0
        ? `Stockout probability reduced by ${Math.abs(stockoutDelta)}% compared to baseline.`
        : `Stockout probability changes by ${stockoutDelta}%.`;

    const inventoryChange = endingInvDelta >= 0
        ? `Ending inventory is projected to increase by +${endingInvDelta} units.`
        : `Ending inventory decreases by ${endingInvDelta} units.`;

    const riskShift = `Safety stock breach duration changes by ${daysBreachDelta} days. Overall score is ${Math.round(rd.score * 100)}/100.`;

    const action = `Approve recommendation: ${rd.decision.title}. This action scores ${Math.round(rd.score * 100)}% on benefit/risk reduction metrics.`;

    return (
        <Dialog
            open={selectedDecision !== null}
            onOpenChange={() => setSelectedDecision(null)}
        >
            <DialogContent className="sm:max-w-[750px] w-full sm:h-[750px] rounded-[1.5rem] border border-slate-200 p-6 overflow-hidden bg-white flex flex-col justify-between">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <DialogHeader className="shrink-0 mb-4">
                        <DialogTitle className="text-xl font-bold text-slate-900 flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-indigo-600 animate-pulse" />
                            {selectedDecision} — {selectedScenario.title}
                        </DialogTitle>
                        <DialogDescription className="text-sm text-slate-500 mt-1">
                            Simulation projection under {selectedCase === 'best' ? 'Best Case' : selectedCase === 'likely' ? 'Most Likely' : 'Worst Case'} scenario assumptions.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto pr-2 space-y-5">
                        <div className="rounded-2xl border border-indigo-100 bg-indigo-50/30 p-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-700">
                                Simulation Summary
                            </h4>
                            <p className="mt-2 text-sm text-slate-700 leading-relaxed font-medium">
                                {summary}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Predicted Demand Impact
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {demandImpact}
                                </p>
                            </div>

                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Inventory Change
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {inventoryChange}
                                </p>
                            </div>

                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Risk Level Shift
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {riskShift}
                                </p>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                Recommended Action
                            </h4>
                            <p className="mt-2 text-sm text-slate-700 leading-relaxed font-medium">
                                {action}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="mt-6 flex justify-end shrink-0">
                    <button
                        onClick={() => setSelectedDecision(null)}
                        className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 transition"
                    >
                        Close Simulation
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

// ==========================================
// MAIN PAGE COMPONENT
// ==========================================


export default function Planning() {
    const [selectedCase, setSelectedCase] = useState<string | null>(null);
    const [selectedDecision, setSelectedDecision] = useState<string | null>(null);
    const [selectedStateCard, setSelectedStateCard] = useState<string | null>(null);

    const [hubFilter, setHubFilter] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('');
    const [productFilter, setProductFilter] = useState('');
    const [dateFilter, setDateFilter] = useState('2024-01-31');
    const [planningWindow, setPlanningWindow] = useState(7);

    const [runRequested, setRunRequested] = useState(false);
    const requestIdRef = useRef(0);

    // Integration States
    const [simulationData, setSimulationData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Dynamic Fixtures Options
    const [fixtures, setFixtures] = useState<PlanningFixtures | null>(null);

    // Fetch unique categories, products, hubs, and dates from backend CSV data
    useEffect(() => {
        let active = true;

        async function fetchFixtures() {
            try {
                const res = await getPlanningFixtures();

                if (active) {
                    setFixtures(res);
                }
            } catch (err: any) {
                console.error("Failed to load planning fixtures:", err);
            }
        }

        fetchFixtures();

        return () => {
            active = false;
        };
    }, []);

    /* ----------------------------------------------------
    HUBS
    ---------------------------------------------------- */
    const availableHubs = useMemo(() => {
        if (!fixtures) return [];

        return [
            ...new Set(
                fixtures.combinations.map(c => String(c.hub_id))
            )
        ].sort((a, b) => Number(a) - Number(b));
    }, [fixtures]);

    /* ----------------------------------------------------
    CATEGORIES (filtered by hub)
    ---------------------------------------------------- */
    const availableCategories = useMemo(() => {
        if (!fixtures) return [];

        return [
            ...new Set(
                fixtures.combinations
                    .filter(
                        c => String(c.hub_id) === hubFilter
                    )
                    .map(c => c.category)
            )
        ].sort();
    }, [fixtures, hubFilter]);

    /* ----------------------------------------------------
    PRODUCTS (filtered by hub + category)
    ---------------------------------------------------- */
    const availableProducts = useMemo(() => {
        if (!fixtures) return [];

        return [
            ...new Set(
                fixtures.combinations
                    .filter(
                        c =>
                            String(c.hub_id) === hubFilter &&
                            c.category === categoryFilter
                    )
                    .map(c => c.product_id)
            )
        ].sort();
    }, [fixtures, hubFilter, categoryFilter]);

    /* ----------------------------------------------------
    DATES (filtered by hub + category + product)
    ---------------------------------------------------- */
    const availableDates = useMemo(() => {
        if (!fixtures) return [];

        const validCombination = fixtures.combinations.some(
            c =>
                String(c.hub_id) === hubFilter &&
                c.category === categoryFilter &&
                c.product_id === productFilter
        );

        if (!validCombination) {
            return [];
        }

        return fixtures.dates ?? [];
    }, [
        fixtures,
        hubFilter,
        categoryFilter,
        productFilter
    ]);

    /* ----------------------------------------------------
    AUTO ALIGN HUB
    ---------------------------------------------------- */
    useEffect(() => {
        if (
            availableHubs.length > 0 &&
            !availableHubs.includes(hubFilter)
        ) {
            setHubFilter(availableHubs[0]);
        }
    }, [availableHubs, hubFilter]);

    /* ----------------------------------------------------
    AUTO ALIGN CATEGORY
    ---------------------------------------------------- */
    useEffect(() => {
        if (
            availableCategories.length > 0 &&
            !availableCategories.includes(categoryFilter)
        ) {
            setCategoryFilter(availableCategories[0]);
        }
    }, [availableCategories, categoryFilter]);

    /* ----------------------------------------------------
    AUTO ALIGN PRODUCT
    ---------------------------------------------------- */
    useEffect(() => {
        if (
            availableProducts.length > 0 &&
            !availableProducts.includes(productFilter)
        ) {
            setProductFilter(availableProducts[0]);
        }
    }, [availableProducts, productFilter]);

    /* ----------------------------------------------------
    AUTO ALIGN DATE
    ---------------------------------------------------- */
    useEffect(() => {
        if (
            availableDates.length > 0 &&
            !availableDates.includes(dateFilter)
        ) {
            setDateFilter(availableDates[0]);
        }
    }, [availableDates, dateFilter]);
    // Call runPlanningSimulation when explicitly requested by user
    useEffect(() => {
        if (!runRequested) {
            return;
        }

        // Prevent running with out-of-sync parameters before auto-alignment completes
        if (!availableProducts.includes(productFilter) || !availableHubs.includes(hubFilter)) {
            setRunRequested(false);
            return;
        }

        const currentRequestId = ++requestIdRef.current;
        let active = true;

        async function fetchSimulation() {
            setLoading(true);
            setError(null);
            try {
                const res = await runPlanningSimulation({
                    hub_id: hubFilter,
                    product_id: productFilter,
                    category: categoryFilter,
                    simulation_date: dateFilter,
                    planning_window_days: planningWindow,
                    n_worlds: 100, // Balanced for lower latency
                    random_seed: 42,
                    skip_llm: true, // Speeds up the run significantly
                });

                if (active && currentRequestId === requestIdRef.current) {
                    setSimulationData(res);
                }
            } catch (err: any) {
                if (active && currentRequestId === requestIdRef.current) {
                    setError(err.message || 'Simulation pipeline failed to run.');
                }
            } finally {
                if (active && currentRequestId === requestIdRef.current) {
                    setLoading(false);
                    setRunRequested(false);
                }
            }
        }
        fetchSimulation();
        return () => {
            active = false;
        };
    }, [runRequested, hubFilter, productFilter, categoryFilter, dateFilter, planningWindow, availableProducts, availableHubs]);

    // Map real backend SimulationState values to card items expected by subcomponents
    const selectedScenario = useMemo(() => {
        const state = simulationData?.scenario;
        return {
            id: 1,
            title: state ? `${state.category} Projection — Hub ${state.hub_id} (${state.product_id})` : 'No Scenario Selected',
            hubId: state ? String(state.hub_id) : '',
            productId: state ? state.product_id : '',
            category: state ? state.category : '',
            riskLevel: (state?.risk?.risk_level || 'LOW') as RiskLevel,
            riskScore: Math.round(state?.risk?.composite_risk_score || 0),
            coverageDays: state?.inventory?.coverage_days || 0,
            currentStock: state?.inventory?.current_stock || 0,
            safetyStock: Math.round(state?.inventory?.safety_stock || 0),
            forecastDemand: Math.round(state?.forecast?.predicted_demand || 0),
            confidenceScore: Math.round((state?.forecast?.confidence_score || 0) * 100),
            demandGrowth: Math.round((state?.demand?.demand_growth_pct || 0) * 100),
            primaryRiskDriver: state?.risk?.primary_risk_driver || 'None',
            replenishmentQty: state?.replenishment?.quantity_ordered || 0,
            etaDays: state?.replenishment?.actual_delay_days || 0,
            recommendation: simulationData?.recommendation_summary?.explanation || 'No recommendation summary generated.',
            situation: state?.inventory?.inventory_status || 'Healthy',
            analysis: state?.risk?.primary_risk_driver || 'Normal parameters',
            inventory: {
                current_stock: state?.inventory?.current_stock || 0,
                coverage_days: state?.inventory?.coverage_days || 0,
                safety_stock: Math.round(state?.inventory?.safety_stock || 0),
                inventory_status: state?.inventory?.inventory_status || 'Healthy',
            },
            demand: {
                demand_growth_pct: state?.demand?.demand_growth_pct || 0,
            },
            forecast: {
                predicted_demand: Math.round(state?.forecast?.predicted_demand || 0),
                confidence_score: state?.forecast?.confidence_score || 0,
            },
            risk: {
                risk_level: state?.risk?.risk_level || 'LOW',
                composite_risk_score: Math.round(state?.risk?.composite_risk_score || 0),
                primary_risk_driver: state?.risk?.primary_risk_driver || 'None',
            },
            event: {
                promotion: state?.event?.promotion || false,
                seasonality: state?.event?.seasonality || 'Standard',
            },
            replenishment: {
                quantity_ordered: state?.replenishment?.quantity_ordered || 0,
                lead_time_days: state?.replenishment?.lead_time_days || 0,
                actual_delay_days: state?.replenishment?.actual_delay_days || 0,
            },
        };
    }, [simulationData]);

    // Dynamically generate decision cards list based on backend ranked decisions
    const decisionsList = useMemo(() => {
        if (simulationData?.ranked_decisions) {
            return simulationData.ranked_decisions.map((rd: any) => {
                let icon = Package;
                if (rd.decision.decision_type.includes('transfer')) {
                    icon = Truck;
                } else if (rd.decision.decision_type.includes('replenishment')) {
                    icon = CalendarDays;
                } else {
                    icon = Activity;
                }

                return {
                    name: rd.decision.title,
                    desc: rd.decision.rationale,
                    icon: icon,
                    id: rd.decision.decision_id,
                    score: rd.score,
                    comparison: rd.comparison,
                };
            });
        }

        return [];
    }, [simulationData]);

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
            <Navbar />

            <main className="max-w-[1900px] w-full mx-auto px-8 py-8 flex flex-col gap-8">

                {/* HERO HEADER */}
                <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-50 via-cyan-50 to-white" />
                    <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-emerald-200/40 blur-3xl" />
                    <div className="absolute bottom-0 left-1/2 h-72 w-72 rounded-full bg-cyan-200/30 blur-3xl" />

                    <div className="relative z-10 p-10">
                        <div>
                            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 text-emerald-700 px-4 py-2 text-sm font-medium">
                                <Sparkles className="h-4 w-4" />
                                AI Planning Workspace
                            </div>

                            <h1 className="mt-6 text-6xl font-bold tracking-tight text-slate-900">
                                Inventory Simulation
                            </h1>

                            <p className="mt-5 max-w-4xl text-lg leading-8 text-slate-600">
                                Detect shortages, simulate future demand,
                                identify inventory risk and generate
                                AI-driven replenishment recommendations
                                before stock issues occur.
                            </p>
                        </div>
                    </div>
                </section>

                {/* 1. Top Filters */}
                <TopFilters
                    hubFilter={hubFilter}
                    setHubFilter={setHubFilter}
                    productFilter={productFilter}
                    setProductFilter={setProductFilter}
                    categoryFilter={categoryFilter}
                    setCategoryFilter={setCategoryFilter}
                    dateFilter={dateFilter}
                    setDateFilter={setDateFilter}
                    planningWindow={planningWindow}
                    setPlanningWindow={setPlanningWindow}
                    categoriesList={availableCategories}
                    productsList={availableProducts}
                    hubsList={availableHubs}
                    datesList={availableDates}
                    onRunSimulation={() => setRunRequested(true)}
                    loading={loading || runRequested}
                    disabled={!availableProducts.includes(productFilter) || !availableHubs.includes(hubFilter)}
                />

                {/* 2. Current State Cards */}
                <StateCards
                    selectedScenario={selectedScenario}
                    setSelectedStateCard={setSelectedStateCard}
                />

                {loading && (
                    <div className="flex items-center justify-center p-8 bg-white border border-slate-200 rounded-[1.5rem] shadow-sm animate-pulse gap-3">
                        <div className="w-6 h-6 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm font-semibold text-slate-600">Running Monte Carlo simulation pipeline...</span>
                    </div>
                )}

                {error && (
                    <div className="p-5 border border-rose-200 bg-rose-50 text-rose-700 rounded-[1.5rem] shadow-sm flex items-start gap-3">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-rose-100 flex items-center justify-center font-bold text-xs font-mono">!</div>
                        <div>
                            <h4 className="font-bold text-sm">Simulation Error</h4>
                            <p className="text-xs mt-1 text-rose-600">{error}</p>
                        </div>
                    </div>
                )}

                {/* 3. Copilot Input Bar */}
                <CopilotInput />

                {/* 4. Case Scenario Cards */}
                <CaseScenarioCards
                    selectedCase={selectedCase}
                    onSelectCase={setSelectedCase}
                />

                {/* 5. Decision Cards */}
                <DecisionCards
                    selectedCase={selectedCase}
                    selectedDecision={selectedDecision}
                    onSelectDecision={setSelectedDecision}
                    decisionsList={decisionsList}
                />

            </main>

            {/* Modals & Dialogs */}
            <StateCardDetailsModal
                selectedStateCard={selectedStateCard}
                setSelectedStateCard={setSelectedStateCard}
                selectedScenario={selectedScenario}
            />

            <ScenarioModal
                caseId={selectedCase}
                onClose={() => setSelectedCase(null)}
                scenario={selectedScenario}
                simulationData={simulationData}
            />

            <DecisionModal
                selectedDecision={selectedDecision}
                setSelectedDecision={setSelectedDecision}
                selectedScenario={selectedScenario}
                selectedCase={selectedCase}
                simulationData={simulationData}
            />

        </div>
    );
}
