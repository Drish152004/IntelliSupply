import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import { Settings2, Sparkles } from 'lucide-react';
import Navbar from '@/components/Navbar';
import EntityScopePanel, { deriveScopeOptions } from '@/components/planning/EntityScopePanel';
import ScenarioInputPanel from '@/components/planning/ScenarioInputPanel';
import RunSimulationBar from '@/components/planning/RunSimulationBar';
import PlanningIdleState from '@/components/planning/PlanningIdleState';
import InventoryStatePanel from '@/components/planning/InventoryStatePanel';
import InventoryStateModal from '@/components/planning/InventoryStateModal';
import OutcomeDiscoveryPanel from '@/components/planning/OutcomeDiscoveryPanel';
import OutcomeDetailModal from '@/components/planning/OutcomeDetailModal';
import InterventionRankingPanel from '@/components/planning/InterventionRankingPanel';
import InterventionDetailModal from '@/components/planning/InterventionDetailModal';
import ExplainabilityPanel from '@/components/planning/ExplainabilityPanel';
import PlanningAutomationModal from '@/components/planning/PlanningAutomationModal';
import {
  getAutomationPolicies,
  getPlanningAuditLogs,
  getPlanningContext,
  simulatePlanning,
  upsertAutomationPolicy,
  understandPlanningScenario,
  PlanningClarificationError,
} from '@/lib/api';
import type {
  ActionAuditLog,
  AutomationPolicy,
  PlanningContext,
  PlanningSimulationResult,
  ScenarioPatch,
} from '@/lib/planningTypes';
import type { PLANNING_EXAMPLE_SCENARIOS } from '@/lib/planningExamples';

export default function Planning() {
  const [context, setContext] = useState<PlanningContext | null>(null);
  const [contextLoading, setContextLoading] = useState(true);
  const [policies, setPolicies] = useState<AutomationPolicy[]>([]);
  const [policiesLoading, setPoliciesLoading] = useState(false);
  const [savingPolicyType, setSavingPolicyType] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<ActionAuditLog[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [automationModalOpen, setAutomationModalOpen] = useState(false);

  const [hubId, setHubId] = useSessionStorageState('planning_hub_id', '');
  const [category, setCategory] = useSessionStorageState('planning_category', '');
  const [productId, setProductId] = useSessionStorageState('planning_product_id', '');
  const [simulationDate, setSimulationDate] = useSessionStorageState('planning_date', '');
  const [planningWindowDays, setPlanningWindowDays] = useSessionStorageState('planning_window', 7);

  const [scenarioQuery, setScenarioQuery] = useSessionStorageState('planning_query', '');
  const [scenarioPatch, setScenarioPatch] = useSessionStorageState<ScenarioPatch | null>('planning_patch', null);
  const [activeExampleId, setActiveExampleId] = useSessionStorageState<string | null>('planning_example_id', null);
  const [clarificationQuestions, setClarificationQuestions] = useSessionStorageState<string[]>('planning_questions', []);

  const [result, setResult] = useSessionStorageState<PlanningSimulationResult | null>('planning_result', null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedStateCard, setSelectedStateCard] = useSessionStorageState<string | null>('planning_state_card', null);
  const [selectedCase, setSelectedCase] = useSessionStorageState<'best' | 'likely' | 'worst' | null>('planning_case', null);
  const [selectedDecisionId, setSelectedDecisionId] = useSessionStorageState<string | null>('planning_decision_id', null);

  const requestIdRef = useRef(0);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await getPlanningContext();
        if (active) setContext(data);
      } catch (err) {
        console.error('Failed to load planning context:', err);
      } finally {
        if (active) setContextLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const loadAutomationData = useCallback(async () => {
    setPoliciesLoading(true);
    setAuditLoading(true);
    try {
      const [policyData, auditData] = await Promise.all([
        getAutomationPolicies(),
        getPlanningAuditLogs(100),
      ]);
      setPolicies(policyData);
      setAuditLogs(auditData);
    } catch (err) {
      console.error('Failed to load automation data:', err);
    } finally {
      setPoliciesLoading(false);
      setAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!automationModalOpen) return;
    loadAutomationData();
  }, [automationModalOpen, loadAutomationData]);

  const { hubs, categories, products, dates } = useMemo(
    () => deriveScopeOptions(context, hubId, category, productId),
    [context, hubId, category, productId],
  );

  useEffect(() => {
    if (hubs.length > 0 && !hubs.includes(hubId)) setHubId(hubs[0]);
  }, [hubs, hubId]);

  useEffect(() => {
    if (categories.length > 0 && !categories.includes(category)) setCategory(categories[0]);
  }, [categories, category]);

  useEffect(() => {
    if (products.length > 0 && !products.includes(productId)) setProductId(products[0]);
  }, [products, productId]);

  useEffect(() => {
    if (dates.length > 0 && !dates.includes(simulationDate)) setSimulationDate(dates[0]);
  }, [dates, simulationDate]);

  const scopeReady = Boolean(hubId && category && productId && simulationDate);
  const scenarioReady = Boolean(
    scenarioPatch || scenarioQuery.trim().length > 0,
  );
  const canRun = scopeReady && scenarioReady && !loading && clarificationQuestions.length === 0;

  const handleSelectExample = useCallback(
    (example: (typeof PLANNING_EXAMPLE_SCENARIOS)[number]) => {
      setScenarioQuery(example.scenarioQuery);
      setScenarioPatch(example.patch);
      setActiveExampleId(example.id);
      setClarificationQuestions([]);
      setError(null);
    },
    [],
  );

  const handleQueryChange = useCallback(() => {
    setActiveExampleId(null);
    setScenarioPatch(null);
    setClarificationQuestions([]);
  }, []);

  const handleRunSimulation = useCallback(async () => {
    if (!scopeReady || !scenarioReady) return;

    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    setClarificationQuestions([]);
    setResult(null);
    setSelectedCase(null);
    setSelectedDecisionId(null);
    setSelectedStateCard(null);

    try {
      let patchToUse = scenarioPatch;

      if (!patchToUse && scenarioQuery.trim()) {
        const understanding = await understandPlanningScenario({
          hub_id: hubId,
          product_id: productId,
          category,
          simulation_date: simulationDate,
          scenario_query: scenarioQuery.trim(),
        });

        if (understanding.status === 'needs_clarification') {
          setClarificationQuestions(understanding.clarification_questions ?? []);
          return;
        }

        patchToUse = understanding.patch ?? null;
        if (patchToUse) {
          setScenarioPatch(patchToUse);
        }
      }

      const data = await simulatePlanning({
        hub_id: hubId,
        product_id: productId,
        category,
        simulation_date: simulationDate,
        scenario_query: scenarioQuery.trim() || undefined,
        patch: patchToUse ?? undefined,
        planning_window_days: planningWindowDays,
        n_worlds: 100,
        random_seed: 42,
        skip_llm: false,
        auto_select_all_decisions: true,
      });

      if (currentRequestId === requestIdRef.current) {
        setResult(data);
        if (automationModalOpen) {
          const updatedLogs = await getPlanningAuditLogs(100);
          setAuditLogs(updatedLogs);
        }
      }
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) return;

      if (err instanceof PlanningClarificationError) {
        setClarificationQuestions(err.questions);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Simulation failed.');
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [
    scopeReady,
    scenarioReady,
    scenarioPatch,
    scenarioQuery,
    hubId,
    productId,
    category,
    simulationDate,
    planningWindowDays,
    automationModalOpen,
  ]);

  const handlePolicyChange = useCallback(
    (policyType: string, patch: Partial<AutomationPolicy>) => {
      setPolicies((prev) =>
        prev.map((policy) =>
          policy.policy_type === policyType
            ? { ...policy, ...patch }
            : policy,
        ),
      );
    },
    [],
  );

  const handleSavePolicy = useCallback(
    async (policyType: string) => {
      const policy = policies.find((item) => item.policy_type === policyType);
      if (!policy) return;
      setSavingPolicyType(policyType);
      try {
        const updated = await upsertAutomationPolicy(policyType, {
          enabled: policy.enabled,
          auto_execute: policy.auto_execute,
          threshold_value: policy.threshold_value,
        });
        setPolicies((prev) =>
          prev.map((item) => (item.policy_type === policyType ? updated : item)),
        );
      } catch (err) {
        console.error('Failed to save policy:', err);
        setError(err instanceof Error ? err.message : 'Failed to save policy.');
      } finally {
        setSavingPolicyType(null);
      }
    },
    [policies],
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="max-w-[1900px] w-full mx-auto px-8 py-8 flex flex-col gap-8">
        <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-50 via-cyan-50 to-white" />
          <div className="relative z-10 p-10">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 text-emerald-700 px-4 py-2 text-sm font-medium">
                  <Sparkles className="h-4 w-4" />
                  Inventory Scenario Simulation
                </div>
                <h1 className="mt-6 text-4xl md:text-5xl font-bold tracking-tight text-slate-900">
                  Planning Agent Workspace
                </h1>
                <p className="mt-4 max-w-3xl text-lg text-slate-600">
                  Select entity scope, describe a what-if scenario, and run simulation to discover outcomes, rank interventions, and generate explainability output.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAutomationModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition"
              >
                <Settings2 className="h-4 w-4 text-indigo-600" />
                Automation Settings
              </button>
            </div>
          </div>
        </section>

        <EntityScopePanel
          hubId={hubId}
          setHubId={setHubId}
          category={category}
          setCategory={setCategory}
          productId={productId}
          setProductId={setProductId}
          simulationDate={simulationDate}
          setSimulationDate={setSimulationDate}
          planningWindowDays={planningWindowDays}
          setPlanningWindowDays={setPlanningWindowDays}
          hubs={hubs}
          categories={categories}
          products={products}
          dates={dates}
          loading={contextLoading}
        />

        <ScenarioInputPanel
          scenarioQuery={scenarioQuery}
          setScenarioQuery={setScenarioQuery}
          activeExampleId={activeExampleId}
          onSelectExample={handleSelectExample}
          clarificationQuestions={clarificationQuestions}
          onQueryChange={handleQueryChange}
          disabled={loading}
        />

        <RunSimulationBar
          canRun={canRun}
          loading={loading}
          onRun={handleRunSimulation}
          scopeReady={scopeReady}
          scenarioReady={scenarioReady}
        />

        {loading && (
          <div className="flex items-center justify-center p-8 bg-white border border-slate-200 rounded-[1.5rem] shadow-sm gap-3">
            <div className="w-6 h-6 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-semibold text-slate-600">Running planning pipeline…</span>
          </div>
        )}

        {error && (
          <div className="p-5 border border-rose-200 bg-rose-50 text-rose-700 rounded-[1.5rem]">
            <h4 className="font-bold text-sm">Simulation Error</h4>
            <p className="text-xs mt-1">{error}</p>
          </div>
        )}

        {!result && !loading && <PlanningIdleState />}

        {result && (
          <>
            <InventoryStatePanel
              scenario={result.scenario}
              onSelectCard={setSelectedStateCard}
            />

            <OutcomeDiscoveryPanel
              outcomes={result.outcomes}
              selectedCase={selectedCase}
              onSelectCase={setSelectedCase}
            />

            <InterventionRankingPanel
              rankedDecisions={result.ranked_decisions}
              recommendation={result.recommendation_summary}
              selectedDecisionId={selectedDecisionId}
              onSelectDecision={setSelectedDecisionId}
            />

            <ExplainabilityPanel explanation={result.llm_explanation} />
          </>
        )}

      </main>

      <PlanningAutomationModal
        open={automationModalOpen}
        onOpenChange={setAutomationModalOpen}
        policies={policies}
        policiesLoading={policiesLoading}
        auditLogs={auditLogs}
        auditLoading={auditLoading}
        onPolicyChange={handlePolicyChange}
        onSavePolicy={handleSavePolicy}
        savingPolicyType={savingPolicyType}
      />

      <InventoryStateModal
        cardId={selectedStateCard}
        scenario={result?.scenario ?? null}
        onClose={() => setSelectedStateCard(null)}
      />

      <OutcomeDetailModal
        caseId={selectedCase}
        outcomes={result?.outcomes ?? null}
        scenario={result?.scenario ?? null}
        onClose={() => setSelectedCase(null)}
      />

      <InterventionDetailModal
        decisionId={selectedDecisionId}
        rankedDecisions={result?.ranked_decisions ?? []}
        recommendation={result?.recommendation_summary ?? null}
        onClose={() => setSelectedDecisionId(null)}
      />
    </div>
  );
}
