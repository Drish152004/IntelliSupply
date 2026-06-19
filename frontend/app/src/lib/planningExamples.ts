import type { ScenarioPatch } from '@/lib/api';

export interface PlanningExampleScenario {
  id: string;
  label: string;
  scenarioQuery: string;
  patch: ScenarioPatch;
}

export const PLANNING_EXAMPLE_SCENARIOS: PlanningExampleScenario[] = [
  {
    id: 'promotion',
    label: 'Launch promotion',
    scenarioQuery: 'What would happen if I launch a promotion?',
    patch: {
      event: { promotion: true },
    },
  },
  {
    id: 'replenishment-delay',
    label: 'Replenishment delay',
    scenarioQuery:
      'What would happen if my incoming replenishment is delayed by 5 days?',
    patch: {
      replenishment: { actual_delay_days_delta: 5 },
    },
  },
  {
    id: 'demand-surge',
    label: 'Demand surge',
    scenarioQuery:
      'What would happen if demand increases by 30% over the next week?',
    patch: {
      demand: { demand_multiplier: 1.3 },
    },
  },
  {
    id: 'epidemic-winter',
    label: 'Epidemic in winter',
    scenarioQuery:
      'What would happen if an epidemic occurs during winter?',
    patch: {
      event: { epidemic: true, seasonality: 'winter' },
    },
  },
];
