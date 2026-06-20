// =======================
// ✅ BASE URL (FIXED)
// =======================

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000'; // ✅ FIXED (NO hostname auto-detection)

const TOKEN_KEY = 'intellisupply_token';

export function getApiBase(): string {
  return API_BASE;
}

// =======================
// ✅ TOKEN MANAGEMENT
// =======================

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function initializeAuth(): void {
  const stored = localStorage.getItem(TOKEN_KEY);
  if (stored) {
    setAccessToken(stored);
  }
}

// =======================
// ✅ ERROR HANDLER
// =======================

export class ApiError extends Error {
  status: number;
  detailData?: unknown;

  constructor(message: string, status: number, detailData?: unknown) {
    super(message);
    this.status = status;
    this.detailData = detailData;
  }
}

// =======================
// ✅ FETCH WRAPPER
// =======================

export interface ApiFetchOptions extends RequestInit {
  auth?: boolean;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const requestHeaders = new Headers(headers);

  // ✅ FIX: do not override FormData content type
  if (!(rest.body instanceof FormData) && rest.body) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  if (auth) {
    const token = getAccessToken();
    if (token) {
      requestHeaders.set('Authorization', `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: requestHeaders,
    credentials: 'include', // ✅ REQUIRED for refresh cookies
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const rawDetail = data.detail;
    const detail =
      typeof rawDetail === 'string'
        ? rawDetail
        : typeof data.message === 'string'
          ? data.message
          : Array.isArray(rawDetail)
            ? rawDetail.map((item: any) => item.msg ?? '').join(', ')
            : typeof rawDetail === 'object' &&
                rawDetail !== null &&
                'clarification_questions' in rawDetail
              ? (rawDetail as { clarification_questions: string[] }).clarification_questions.join(' ')
              : 'Request failed';

    throw new ApiError(detail, response.status, rawDetail);
  }

  return data as T;
}

// =======================
// ✅ AUTH TYPES
// =======================

export interface AuthUserResponse {
  id?: string;
  name: string;
  email: string;
  role: string;
  role_id?: number;
  courier_id?: string;
}

export interface LoginResponse {
  success: boolean;
  access_token: string;
  token_type: string;
  user: AuthUserResponse;
  message?: string;
}

// =======================
// ✅ AUTH API
// =======================

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    auth: false,
  });
}

export async function googleLoginApi(idToken: string, role: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/google-login', {
    method: 'POST',
    body: JSON.stringify({
      id_token: idToken,
      role,
    }),
    auth: false,
  });
}

export async function refreshSessionApi(): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/refresh', {
    method: 'POST',
    auth: false,
  });
}

export async function logoutApi(): Promise<{ success: boolean; message?: string }> {
  return apiFetch<{ success: boolean; message?: string }>('/api/logout', {
    method: 'POST',
    auth: false,
  });
}

export async function fetchCurrentUser(): Promise<AuthUserResponse> {
  const data = await apiFetch<{ success: boolean; user: AuthUserResponse }>('/api/me');
  return data.user;
}

export async function updateCurrentUser(payload: { name?: string }): Promise<AuthUserResponse> {
  const data = await apiFetch<{ success: boolean; user: AuthUserResponse }>('/api/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return data.user;
}

// =======================
// ✅ SHIPMENTS
// =======================

export interface CreateShipmentPayload {
  from_hub_name: string;
  to_hub_name: string;
  delivery_date: string;
  receipt_time?: string;
  notes?: string;
}

export interface OrderDetail {
  order_id: string;
  city_name?: string;
  ds?: number;
  delivery_day?: string;
  receipt_time?: string;
  from_hub_name?: string;
  from_lat?: number;
  from_lon?: number;
  to_hub_name?: string;
  to_lat?: number;
  to_lon?: number;
  assigned_courier_id?: string;
  assigned_courier_name?: string;
  assigned_courier_email?: string;
  assigned_courier_hub_name?: string;
  nearest_courier_distance_m?: number;
  typecode?: string;
  aoi_id?: string;
  notes?: string;
}

export interface ShipmentListItem {
  order_id: string;
  from_hub_name?: string;
  to_hub_name?: string;
  city_name?: string;
  delivery_day?: string;
  receipt_time?: string;
  assigned_courier_id?: string;
  assigned_courier_name?: string;
  status?: string;
}

export interface CreateShipmentResult {
  success: boolean;
  message: string;
  order?: any;
}

export async function createShipment(payload: CreateShipmentPayload): Promise<CreateShipmentResult> {
  return apiFetch('/orders/shipments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
// =======================
// ✅ CONTINUED FEATURES
// =======================

export async function listCities() {
  const data = await apiFetch<{ cities: any[] }>('/orders/cities');
  return data.cities;
}

export async function listHubs(cityName: string) {
  const params = new URLSearchParams({ city_name: cityName });
  const data = await apiFetch<{ hubs: any[] }>(`/orders/hubs?${params}`);
  return data.hubs;
}

export interface HubMapLocation {
  hub_id: number | string;
  hub_name: string;
  city_name?: string;
  lat: number;
  lng: number;
  hub_type?: string;
}

export async function listHubLocations(): Promise<HubMapLocation[]> {
  const data = await apiFetch<{ hubs: HubMapLocation[] }>('/orders/hub-locations');
  return data.hubs;
}

export interface ListShipmentsOptions {
  limit?: number;
  courierId?: string;
  deliveryDay?: string;
}

export async function listDeliveryDays(): Promise<string[]> {
  const data = await apiFetch<{ delivery_days: string[] }>('/orders/delivery-days');
  return data.delivery_days;
}

export async function listShipments(options: ListShipmentsOptions | number = {}): Promise<ShipmentListItem[]> {
  if (typeof options === 'number') {
    options = { limit: options };
  }
  const { limit = 50, courierId, deliveryDay } = options;
  const params = new URLSearchParams({ limit: String(limit) });
  if (courierId) params.set('courier_id', courierId);
  if (deliveryDay) params.set('delivery_day', deliveryDay);
  const data = await apiFetch<{ shipments: ShipmentListItem[] }>(`/orders/shipments?${params.toString()}`);
  return data.shipments;
}

export async function getShipment(orderId: string) {
  const data = await apiFetch<{ order: any }>(`/orders/${orderId}`);
  return data.order;
}

export async function listCouriers(limit = 200) {
  const data = await apiFetch<{ couriers: any[] }>(`/couriers?limit=${limit}`);
  return data.couriers;
}

export async function listCouriersWithOrders(day: string) {
  const params = new URLSearchParams({
    delivery_day: day,
    with_orders_only: 'true',
  });

  const data = await apiFetch<{ couriers: any[] }>(`/couriers?${params}`);
  return data.couriers;
}

export interface RouteStop {
  sequence: number;
  order_id: string;
  from_hub_name?: string;
  to_hub_name?: string;
  from_lat?: number;
  from_lng?: number;
  to_lat?: number;
  to_lng?: number;
  lat_wgs84?: number;
  lon_wgs84?: number;
  city_name?: string;
  delivery_day?: string;
  eta_minutes: number;
  eta_from_start_minutes: number;
  estimated_arrival: string;
}

export interface CourierStartPoint {
  lat: number;
  lng: number;
  name?: string;
}

export interface CourierRouteResult {
  courier_id: string;
  courier_name?: string;
  delivery_day: string;
  route_start_time: string;
  predicted_sequence: string[];
  stops: RouteStop[];
  total_eta_minutes: number;
  source?: 'graphdb' | 'ml_model' | 'graph_built';
  courier_start?: CourierStartPoint | null;
  path?: [number, number][];
}

export async function predictCourierRoute(
  courierId: 'me' | string,
  deliveryDay: string,
): Promise<CourierRouteResult> {
  return apiFetch<CourierRouteResult>(`/couriers/${courierId}/route`, {
    method: 'POST',
    body: JSON.stringify({ delivery_day: deliveryDay }),
  });
}

// =======================
// ✅ USERS
// =======================

export async function listUsers(limit = 100) {
  const data = await apiFetch<{ users: any[] }>(`/api/users?limit=${limit}`);
  return data.users;
}

export async function registerUser(payload: any) {
  return apiFetch('/api/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function createCourierFrontend(payload: any) {
  return apiFetch('/couriers', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// =======================
// ✅ INVENTORY
// =======================

export async function listInventoryProducts(search = '', category = '') {
  const params = new URLSearchParams({ search, category });
  const data = await apiFetch<{ products: any[] }>(`/inventory/products?${params}`);
  return data.products;
}

export async function getInventorySummary() {
  const data = await apiFetch<{ summary: any }>('/inventory/summary');
  return data.summary;
}

export async function getInventoryForecastTrend() {
  const data = await apiFetch<{ trend: any[] }>('/inventory/forecast-trend');
  return data.trend;
}

export async function createInventoryProduct(payload: any) {
  const data = await apiFetch<{ product: any }>('/inventory/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return data.product;
}

export async function updateInventoryProduct(id: string, payload: any) {
  const data = await apiFetch<{ product: any }>(`/inventory/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return data.product;
}

export async function deleteInventoryProduct(id: string) {
  await apiFetch(`/inventory/products/${id}`, { method: 'DELETE' });
}
export interface InventoryProduct {
  id: string;
  product_id?: string;
  name: string;
  category?: string;
  unit_price?: number | null;
  supplier_name?: string | null;
  stock: number;
  demand?: number;
  status: string;
}

export interface InventoryCategoryItem {
  category: string;
}

export interface InventoryCatalogProduct {
  id?: number;
  product_id: string;
  category: string;
  product_name: string;
  product_display_name?: string | null;
}

export interface InventoryCityItem {
  city_id: number;
  city_name: string;
}

export interface InventoryHubItem {
  hub_id: number;
  hub_name?: string | null;
  city_id?: number | null;
  hub_type?: string | null;
}

export interface CreateInventoryStockEntryPayload {
  category: string;
  product_id: string;
  city_id: number;
  hub_id: number;
  inventory_level: number;
  units_ordered?: number;
  price?: number;
  demand?: number;
  discount?: number;
  weather_condition?: string;
  seasonality?: string;
  promotion?: number;
  epidemic?: number;
}

export async function listInventoryCategories(): Promise<string[]> {
  const data = await apiFetch<{ categories: string[] }>('/inventory/categories');
  return data.categories;
}

export async function listInventoryProductsByCategory(
  category: string,
): Promise<InventoryCatalogProduct[]> {
  const params = new URLSearchParams({ category });
  const data = await apiFetch<{ products: InventoryCatalogProduct[] }>(
    `/inventory/products/by-category?${params.toString()}`,
  );
  return data.products;
}

export async function listInventoryCities(): Promise<InventoryCityItem[]> {
  const data = await apiFetch<{ cities: InventoryCityItem[] }>('/inventory/cities');
  return data.cities;
}

export async function listInventoryHubs(
  cityId: number | string,
): Promise<InventoryHubItem[]> {
  const params = new URLSearchParams({ city_id: String(cityId) });
  const data = await apiFetch<{ hubs: InventoryHubItem[] }>(
    `/inventory/hubs?${params.toString()}`,
  );
  return data.hubs;
}

export async function createInventoryStockEntry(
  payload: CreateInventoryStockEntryPayload,
): Promise<InventoryProduct> {
  const data = await apiFetch<{ product: InventoryProduct }>('/inventory/stock-entry', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  return data.product;
}
// =======================
// ✅ COPILOT
// =======================

export interface CopilotResponse {
  status: string;
  message?: string;
  question?: string;
  answer?: string;
  reason?: string;
  role?: string;
  task?: string;
  source?: string;
  clarification_type?: string;
  missing_fields?: string[];
  data?: Record<string, unknown>;
}

export interface CopilotSessionPayload {
  logisticsSession?: Record<string, unknown> | null;
  inventorySession?: Record<string, unknown> | null;
  pendingClarificationSession?: Record<string, unknown> | null;
}

export async function queryCopilot(
  query: string,
  sessions?: CopilotSessionPayload,
): Promise<CopilotResponse> {
  return apiFetch<CopilotResponse>('/copilot/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      logistics_session: sessions?.logisticsSession ?? undefined,
      inventory_session: sessions?.inventorySession ?? undefined,
      pending_clarification_session: sessions?.pendingClarificationSession ?? undefined,
    }),
  });
}

// =======================
// ✅ VOICE
// =======================

export async function transcribeVoice(audio: Blob) {
  const form = new FormData();
  form.append('audio', audio);

  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: 'POST',
    body: form,
    headers,
    credentials: 'include',
  });

  const data = await res.json();
  if (!res.ok) throw new ApiError('Voice transcription failed', res.status);

  return data;
}

// =======================
//  DASHBOARD + NOTIFS
// =======================

export interface LogisticsCallout {
  title: string;
  detail: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface LogisticsKpis {
  delivery_day: string;
  active_shipments: number;
  at_risk_shipments: number;
  active_couriers: number;
  hub_coverage: number;
  unassigned_shipments: number;
  courier_assignment_pct: number;
  callouts: LogisticsCallout[];
}

export interface RoleDistributionEntry {
  role: string;
  count: number;
}

export interface DashboardSummary {
  recent_shipments: number;
  courier_assignment_pct: number;
  active_couriers: number;
  total_accounts: number;
  unassigned_shipments: number;
  hub_count: number;
  reference_delivery_day: string;
  inventory_summary?: Record<string, unknown> | null;
  role_distribution: RoleDistributionEntry[];
  logistics: LogisticsKpis;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const data = await apiFetch<{ summary: DashboardSummary }>('/api/dashboard/summary');
  return data.summary;
}

export async function getLogisticsKpis(deliveryDay?: string): Promise<LogisticsKpis> {
  const params = deliveryDay ? `?delivery_day=${encodeURIComponent(deliveryDay)}` : '';
  const data = await apiFetch<{ kpis: LogisticsKpis }>(`/api/dashboard/logistics-kpis${params}`);
  return data.kpis;
}

export async function listNotifications(limit = 20) {
  const data = await apiFetch<{ notifications: any[] }>(`/api/notifications?limit=${limit}`);
  return data.notifications;
}

export async function getUnreadNotificationCount() {
  const data = await apiFetch<{ unread_count: number }>(
    '/api/notifications/unread-count'
  );
  return data.unread_count;
}

export async function markNotificationRead(id: string) {
  const data = await apiFetch<{ notification: any }>(
    `/api/notifications/${id}/read`,
    { method: 'PATCH' }
  );
  return data.notification;
}

export async function markAllNotificationsRead() {
  const data = await apiFetch<{ updated_count: number }>(
    '/api/notifications/read-all',
    { method: 'PATCH' }
  );
  return data.updated_count;
}

export type {
  ActionAuditLog,
  AutomationPolicy,
  ExecutePlanningDecisionPayload,
  ExecutePlanningDecisionResult,
  ManualExecutionStatus,
  ScenarioPatch,
  PlanningContext,
  ScenarioUnderstandingResult,
  PlanningSimulationResult,
  SimulatePlanningPayload,
  UnderstandScenarioPayload,
  EntityScope,
} from './planningTypes';

export {
  mapSimulationDay,
  mapDailyLog,
  asBoolFlag,
  formatPercentFraction,
  formatPatchLabels,
  PlanningClarificationError,
} from './planningTypes';

import type {
  ActionAuditLog,
  AutomationPolicy,
  ExecutePlanningDecisionPayload,
  ExecutePlanningDecisionResult,
  PlanningContext,
  PlanningSimulationResult,
  ScenarioUnderstandingResult,
  SimulatePlanningPayload,
  UnderstandScenarioPayload,
} from './planningTypes';
import { PlanningClarificationError } from './planningTypes';

export async function getPlanningContext(): Promise<PlanningContext> {
  return apiFetch<PlanningContext>('/planning/context');
}

export async function understandPlanningScenario(
  payload: UnderstandScenarioPayload,
): Promise<ScenarioUnderstandingResult> {
  return apiFetch<ScenarioUnderstandingResult>('/planning/understand', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function simulatePlanning(
  payload: SimulatePlanningPayload,
): Promise<PlanningSimulationResult> {
  try {
    return await apiFetch<PlanningSimulationResult>('/planning/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 422) {
      const detail = err.detailData as
        | { status?: string; clarification_questions?: string[] }
        | undefined;
      if (
        detail &&
        typeof detail === 'object' &&
        detail.status === 'needs_clarification' &&
        Array.isArray(detail.clarification_questions)
      ) {
        throw new PlanningClarificationError(detail.clarification_questions);
      }
    }
    throw err;
  }
}

export async function getAutomationPolicies(): Promise<AutomationPolicy[]> {
  const data = await apiFetch<{ policies: AutomationPolicy[] }>('/automation/policies');
  return data.policies;
}

export async function upsertAutomationPolicy(
  policyType: string,
  payload: Pick<
    AutomationPolicy,
    'enabled' | 'auto_execute' | 'threshold_value'
  >,
): Promise<AutomationPolicy> {
  const data = await apiFetch<{ policy: AutomationPolicy }>(
    `/automation/policies/${encodeURIComponent(policyType)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
  );
  return data.policy;
}

export async function getPlanningAuditLogs(limit = 100): Promise<ActionAuditLog[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  const data = await apiFetch<{ logs: ActionAuditLog[] }>(`/automation/audit-logs?${params.toString()}`);
  return data.logs;
}

export async function executePlanningDecision(
  payload: ExecutePlanningDecisionPayload,
): Promise<ExecutePlanningDecisionResult> {
  return apiFetch<ExecutePlanningDecisionResult>('/automation/execute', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}



