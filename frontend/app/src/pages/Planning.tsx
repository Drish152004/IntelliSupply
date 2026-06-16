import { useState } from 'react';
import Navbar from '@/components/Navbar';
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

const scenarios: Scenario[] = [
    {
        id: 1,
        title: 'HYD Smartphone Shortage',
        hubId: 'HYD-01',
        productId: 'SMARTPHONE-X',
        category: 'Electronics',
        riskLevel: 'HIGH',
        riskScore: 89,
        coverageDays: 5,
        currentStock: 2450,
        safetyStock: 3200,
        forecastDemand: 5200,
        confidenceScore: 93,
        demandGrowth: 24,
        primaryRiskDriver: 'Demand Surge',
        replenishmentQty: 1200,
        etaDays: 3,
        recommendation:
            'Transfer 450 units from BLR Hub and immediately raise PO for 1200 units.',
        situation:
            'Inventory projected to fall below safety stock within 5 days.',
        analysis:
            'Demand has increased significantly while inbound supply remains unchanged.',
    },
    {
        id: 2,
        title: 'BLR Supplier Delay',
        hubId: 'BLR-02',
        productId: 'TABLET-A',
        category: 'Electronics',
        riskLevel: 'MEDIUM',
        riskScore: 63,
        coverageDays: 11,
        currentStock: 6100,
        safetyStock: 4500,
        forecastDemand: 3900,
        confidenceScore: 90,
        demandGrowth: 11,
        primaryRiskDriver: 'Inbound Delay',
        replenishmentQty: 2000,
        etaDays: 7,
        recommendation:
            'Reallocate inventory from CHN hub until delayed shipment arrives.',
        situation:
            'Supplier shipment delayed by 4 days.',
        analysis:
            'Stock remains healthy but risk increases if delay extends further.',
    },
    {
        id: 3,
        title: 'CHN Seasonal Demand Spike',
        hubId: 'CHN-03',
        productId: 'HEADPHONE-Z',
        category: 'Accessories',
        riskLevel: 'HIGH',
        riskScore: 81,
        coverageDays: 7,
        currentStock: 3700,
        safetyStock: 3000,
        forecastDemand: 6200,
        confidenceScore: 95,
        demandGrowth: 38,
        primaryRiskDriver: 'Seasonality',
        replenishmentQty: 1800,
        etaDays: 4,
        recommendation:
            'Increase reorder quantity by 25% for next cycle.',
        situation:
            'Upcoming promotion expected to significantly increase sales.',
        analysis:
            'Historical promotion patterns indicate delayed demand spike.',
    },
    {
        id: 4,
        title: 'MUM Overstock Risk',
        hubId: 'MUM-04',
        productId: 'MONITOR-27',
        category: 'Peripherals',
        riskLevel: 'LOW',
        riskScore: 22,
        coverageDays: 42,
        currentStock: 9200,
        safetyStock: 2400,
        forecastDemand: 1800,
        confidenceScore: 91,
        demandGrowth: -8,
        primaryRiskDriver: 'Excess Inventory',
        replenishmentQty: 0,
        etaDays: 0,
        recommendation:
            'Pause replenishment and redistribute inventory to nearby hubs.',
        situation:
            'Inventory significantly exceeds projected demand.',
        analysis:
            'Demand decline causing inventory accumulation.',
    },
];

const generateCaseSimulation = (scenario: Scenario, caseId: string): CaseSimulationData => {
    const totalDays = 10;
    const logs: DailyLogEntry[] = [];
    let currentInv = scenario.currentStock;
    const safetyStock = scenario.safetyStock;

    let demandMultiplier = 1.0;
    let eta = scenario.etaDays;

    if (caseId === 'best') {
        demandMultiplier = 0.75;
        eta = Math.max(1, scenario.etaDays - 1);
    } else if (caseId === 'likely') {
        demandMultiplier = 1.0;
        eta = scenario.etaDays;
    } else if (caseId === 'worst') {
        demandMultiplier = 1.4;
        eta = scenario.etaDays + 3;
    }

    const dailyDemandAverage = Math.round(scenario.forecastDemand / 15);

    let minimumInventory = currentInv;
    let stockoutOccurredTotal = false;
    let firstStockoutDay: number | string = 'N/A';
    let totalShortage = 0;
    let safetyStockBreachedTotal = false;
    let daysBelowSafetyStock = 0;

    for (let day = 1; day <= totalDays; day++) {
        const startInv = currentInv;
        const dayDemand = Math.round(dailyDemandAverage * demandMultiplier * (0.95 + (day % 3) * 0.05));

        let repReceived = 0;
        if (day === eta && scenario.replenishmentQty > 0) {
            repReceived = scenario.replenishmentQty;
        }

        let endInv = startInv - dayDemand + repReceived;
        let dayStockout = false;
        if (endInv < 0) {
            dayStockout = true;
            totalShortage += Math.abs(endInv);
            endInv = 0;
        }

        if (endInv < safetyStock) {
            daysBelowSafetyStock++;
        }

        if (endInv < minimumInventory) {
            minimumInventory = endInv;
        }

        if (dayStockout) {
            stockoutOccurredTotal = true;
            if (firstStockoutDay === 'N/A') {
                firstStockoutDay = day;
            }
        }

        currentInv = endInv;

        logs.push({
            day,
            startingInventory: startInv,
            demand: dayDemand,
            replenishmentReceived: repReceived,
            endingInventory: endInv,
            stockoutOccurred: dayStockout,
            belowSafetyStock: endInv < safetyStock,
        });
    }

    if (minimumInventory < safetyStock) {
        safetyStockBreachedTotal = true;
    }

    const worldId = `SIM-${scenario.hubId.split('-')[0]}-${caseId.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`;

    return {
        world_id: worldId,
        ending_inventory: currentInv,
        minimum_inventory: minimumInventory,
        stockout_occurred: stockoutOccurredTotal,
        stockout_day: firstStockoutDay,
        shortage_quantity: totalShortage,
        safety_stock_breached: safetyStockBreachedTotal,
        days_below_safety_stock: daysBelowSafetyStock,
        daily_log: JSON.stringify(logs),
    };
};

const getSimulationResult = (scenarioCase: string, decision: string, scenario: Scenario) => {
    const hub = scenario.hubId;
    const product = scenario.productId;

    let summary = '';
    let demandImpact = '';
    let inventoryChange = '';
    let riskShift = '';
    let action = '';

    if (scenarioCase === 'best') {
        if (decision === 'Reallocate Inventory') {
            summary = `Successful stock transfer under optimistic conditions. Shortage resolved with minimal cost.`;
            demandImpact = `Stable demand allows reallocation to cover 100% of pending orders.`;
            inventoryChange = `Inventory at ${hub} increased by 450 units; helper hub remains above safety threshold.`;
            riskShift = `Risk level drops from ${scenario.riskLevel} to LOW (Risk Score: 15).`;
            action = `Approve reallocation order and initiate truck transfer immediately.`;
        } else if (decision === 'Increase Purchase Order') {
            summary = `Emergency PO successfully expedited. Supplier confirms immediate dispatch.`;
            demandImpact = `Strong demand absorbed by new stock arrival in 2 days.`;
            inventoryChange = `Stock level reaches ${scenario.currentStock + 1200} units, restoring healthy buffer.`;
            riskShift = `Risk level drops to LOW (Risk Score: 20).`;
            action = `Confirm PO with finance team and track shipment.`;
        } else if (decision === 'Delay Replenishment') {
            summary = `Replenishment delay managed without stockout due to high beginning inventory.`;
            demandImpact = `No demand impact; existing stock is sufficient for current cycle.`;
            inventoryChange = `No immediate change; delayed shipment scheduled in 7 days.`;
            riskShift = `Risk level remains stable.`;
            action = `Monitor daily sales to ensure stock levels don't drop unexpectedly.`;
        } else {
            summary = `No intervention taken. High market confidence prevents any severe fallout.`;
            demandImpact = `Normal demand patterns persist.`;
            inventoryChange = `Inventory naturally draws down to safety levels.`;
            riskShift = `Risk level drops slightly to MEDIUM.`;
            action = `Continue standard operations and check status in 48 hours.`;
        }
    } else if (scenarioCase === 'likely') {
        if (decision === 'Reallocate Inventory') {
            summary = `Moderate success. Stock transfer covers the immediate deficit but tightens supply elsewhere.`;
            demandImpact = `Covers 85% of projected demand spike for ${product}.`;
            inventoryChange = `Restores safety stock level to ${scenario.safetyStock} units at ${hub}.`;
            riskShift = `Risk level reduces from ${scenario.riskLevel} to MEDIUM.`;
            action = `Execute partial transfer and prepare backup purchase orders.`;
        } else if (decision === 'Increase Purchase Order') {
            summary = `New PO generated. Restores inventory safety stock in 4 days.`;
            demandImpact = `Demand satisfied, but higher logistics fees reduce margin by 5%.`;
            inventoryChange = `Inventory will increase by ${scenario.replenishmentQty || 1200} units on ETA day.`;
            riskShift = `Risk level reduces to LOW/MEDIUM.`;
            action = `Raise purchase order and approve express delivery fee.`;
        } else if (decision === 'Delay Replenishment') {
            summary = `Delaying replenishment increases risk of inventory depletion.`;
            demandImpact = `Potential 10% lost sales if demand surges during delay.`;
            inventoryChange = `Current stock will drop to ${scenario.currentStock - 1000} units before shipment arrival.`;
            riskShift = `Risk level increases to HIGH.`;
            action = `Avoid delaying replenishment unless storage space is fully capped.`;
        } else {
            summary = `No action taken. Inventory is highly likely to fall below safety threshold.`;
            demandImpact = `Expected stockout in ${scenario.coverageDays} days.`;
            inventoryChange = `Inventory drops below safety threshold (${scenario.safetyStock} units).`;
            riskShift = `Risk level remains at ${scenario.riskLevel}.`;
            action = `Urgent action recommended: initiate reallocation or PO.`;
        }
    } else {
        if (decision === 'Reallocate Inventory') {
            summary = `Ineffective reallocation. High demand across all regions limits available helper stock.`;
            demandImpact = `Only covers 40% of demand; critical stockouts expected at multiple hubs.`;
            inventoryChange = `Stock increases marginally at ${hub} but depletes other regional centers.`;
            riskShift = `Risk level remains HIGH.`;
            action = `Combine reallocation with emergency local vendor sourcing.`;
        } else if (decision === 'Increase Purchase Order') {
            summary = `Expedited PO delayed due to supply chain congestion. Arrival takes 5+ days.`;
            demandImpact = `Severe demand backlog; customer satisfaction drops.`;
            inventoryChange = `Inventory remains critical until delayed PO arrives.`;
            riskShift = `Risk level remains HIGH.`;
            action = `Request partial split-shipment delivery from supplier.`;
        } else if (decision === 'Delay Replenishment') {
            summary = `Disastrous delay. Critical stockout occurs within 48 hours.`;
            demandImpact = `40% of sales orders unfulfilled; severe penalties from clients.`;
            inventoryChange = `Stock levels drop to zero at ${hub}.`;
            riskShift = `Risk level escalates to CRITICAL.`;
            action = `Cancel replenishment delay immediately; trigger emergency supplies.`;
        } else {
            summary = `No action taken under severe conditions. Major supply disruption.`;
            demandImpact = `Immediate stockout for ${product} at ${hub}.`;
            inventoryChange = `Inventory drops to zero; pending orders accumulate.`;
            riskShift = `Risk level rises to CRITICAL (Risk Score: 98).`;
            action = `Convene emergency supply chain board to approve immediate purchase order.`;
        }
    }

    return { summary, demandImpact, inventoryChange, riskShift, action };
};

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
}: TopFiltersProps) {
    return (
        <div className="flex flex-wrap items-center gap-6 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm animate-fade-in">
            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Hub</label>
                <select
                    value={hubFilter}
                    onChange={(e) => setHubFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    <option value="ALL">All Hubs</option>
                    <option value="HYD-01">Hyderabad (HYD-01)</option>
                    <option value="BLR-02">Bangalore (BLR-02)</option>
                    <option value="CHN-03">Chennai (CHN-03)</option>
                    <option value="MUM-04">Mumbai (MUM-04)</option>
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Product ID</label>
                <select
                    value={productFilter}
                    onChange={(e) => setProductFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    <option value="ALL">All Products</option>
                    <option value="SMARTPHONE-X">SMARTPHONE-X</option>
                    <option value="TABLET-A">TABLET-A</option>
                    <option value="HEADPHONE-Z">HEADPHONE-Z</option>
                    <option value="MONITOR-27">MONITOR-27</option>
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</label>
                <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    <option value="ALL">All Categories</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Accessories">Accessories</option>
                    <option value="Peripherals">Peripherals</option>
                </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[150px] flex-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Date</label>
                <input
                    type="date"
                    value={dateFilter}
                    onChange={(e) => setDateFilter(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-1.5 text-sm bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                />
            </div>
        </div>
    );
}

interface StateCardsProps {
    selectedScenario: Scenario;
    setSelectedStateCard: (card: string) => void;
}

export function StateCards({ selectedScenario, setSelectedStateCard }: StateCardsProps) {
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
                            Stock: {selectedScenario.currentStock.toLocaleString()} | {selectedScenario.coverageDays} days remaining
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
                            Forecast: {selectedScenario.forecastDemand.toLocaleString()} | +{selectedScenario.demandGrowth}% growth trend
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
                            Level: {selectedScenario.riskLevel} | Composite score: {selectedScenario.riskScore}/100
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
                            Driver: {selectedScenario.primaryRiskDriver} | Category: {selectedScenario.category}
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
                            Inbound PO: {selectedScenario.replenishmentQty.toLocaleString()} units | ETA: {selectedScenario.etaDays} days
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
}

export function DecisionCards({ selectedCase, selectedDecision, onSelectDecision }: DecisionCardsProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-800">Select Simulation Decision</h2>
                <span className="text-xs font-semibold text-slate-400">
                    (Impact calculated under {selectedCase ? (selectedCase === 'best' ? 'Best Case' : selectedCase === 'likely' ? 'Most Likely' : 'Worst Case') : 'Most Likely'} scenario)
                </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    {
                        name: 'Reallocate Inventory',
                        desc: 'Transfer stock from BLR-02 or CHN-03 to cover immediate deficits.',
                        icon: Truck,
                        color: 'indigo',
                    },
                    {
                        name: 'Increase Purchase Order',
                        desc: 'Place an emergency order for 1,200 additional units immediately.',
                        icon: Package,
                        color: 'sky',
                    },
                    {
                        name: 'Delay Replenishment',
                        desc: 'Reschedule incoming delivery dates to match hub capacity constraints.',
                        icon: CalendarDays,
                        color: 'amber',
                    },
                    {
                        name: 'Do Nothing',
                        desc: 'Maintain current supply chain parameters and monitor daily stock rates.',
                        icon: Activity,
                        color: 'slate',
                    },
                ].map((dec) => {
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
}

export function ScenarioModal({ caseId, onClose, scenario }: ScenarioModalProps) {
    const [activeTab, setActiveTab] = useState<'summary' | 'timeline'>('summary');

    if (!caseId) return null;

    const simData = generateCaseSimulation(scenario, caseId);
    const logEntries = JSON.parse(simData.daily_log) as DailyLogEntry[];
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
}

export function DecisionModal({
    selectedDecision,
    setSelectedDecision,
    selectedScenario,
    selectedCase,
}: DecisionModalProps) {
    if (!selectedDecision) return null;

    const res = getSimulationResult(selectedCase || 'likely', selectedDecision, selectedScenario);

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
                                {res.summary}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Predicted Demand Impact
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {res.demandImpact}
                                </p>
                            </div>

                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Inventory Change
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {res.inventoryChange}
                                </p>
                            </div>

                            <div className="rounded-xl border border-slate-200 p-4 bg-slate-50/50">
                                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    Risk Level Shift
                                </h5>
                                <p className="mt-2 text-sm text-slate-700 leading-normal font-semibold">
                                    {res.riskShift}
                                </p>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                Recommended Action
                            </h4>
                            <p className="mt-2 text-sm text-slate-700 leading-relaxed font-medium">
                                {res.action}
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

    const [hubFilter, setHubFilter] = useState('ALL');
    const [productFilter, setProductFilter] = useState('ALL');
    const [categoryFilter, setCategoryFilter] = useState('ALL');
    const [dateFilter, setDateFilter] = useState('2026-06-15');

    const selectedScenario = scenarios.find(s => {
        if (hubFilter !== 'ALL' && s.hubId !== hubFilter) return false;
        if (productFilter !== 'ALL' && s.productId !== productFilter) return false;
        if (categoryFilter !== 'ALL' && s.category !== categoryFilter) return false;
        return true;
    }) || scenarios[0];

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
                />

                {/* 2. Current State Cards */}
                <StateCards
                    selectedScenario={selectedScenario}
                    setSelectedStateCard={setSelectedStateCard}
                />

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
            />

            <DecisionModal
                selectedDecision={selectedDecision}
                setSelectedDecision={setSelectedDecision}
                selectedScenario={selectedScenario}
                selectedCase={selectedCase}
            />

        </div>
    );
}
