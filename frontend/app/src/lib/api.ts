// const getBaseUrl = () => {
//   if (import.meta.env.VITE_API_URL) {
//     return import.meta.env.VITE_API_URL;
//   }
//   if (import.meta.env.VITE_API_BASE_URL) {
//     return import.meta.env.VITE_API_BASE_URL;
//   }
//   const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
//   return `http://${hostname}:8000`;
// };

// const API_BASE = getBaseUrl();

// const TOKEN_KEY = 'intellisupply_token';

// export function getApiBase(): string {
//   return API_BASE;
// }

// export function getAccessToken(): string | null {
//   return localStorage.getItem(TOKEN_KEY);
// }

// export function setAccessToken(token: string | null): void {
//   if (token) {
//     localStorage.setItem(TOKEN_KEY, token);
//   } else {
//     localStorage.removeItem(TOKEN_KEY);
//   }
// }
// //  ADD THIS EXACT FUNCTION
// export function initializeAuth(): void {
//   const stored = localStorage.getItem(TOKEN_KEY);
//   if (stored) {
//     setAccessToken(stored);
//   }
// }

// export class ApiError extends Error {
//   status: number;

//   constructor(message: string, status: number) {
//     super(message);
//     this.status = status;
//   }
// }

// export interface ApiFetchOptions extends RequestInit {
//   auth?: boolean;
// }

// export async function apiFetch<T = unknown>(
//   path: string,
//   options: ApiFetchOptions = {},
// ): Promise<T> {
//   const { auth = true, headers, ...rest } = options;
//   const requestHeaders = new Headers(headers);

//   if (!requestHeaders.has('Content-Type') && rest.body) {
//     requestHeaders.set('Content-Type', 'application/json');
//   }

//   if (auth) {
//     const token = getAccessToken();
//     if (token) {
//       requestHeaders.set('Authorization', `Bearer ${token}`);
//     }
//   }

//   const response = await fetch(`${API_BASE}${path}`, {
//     ...rest,
//     headers: requestHeaders,
//     credentials: 'include',
//   });

//   const data = await response.json().catch(() => ({}));

//   if (!response.ok) {
//     const detail =
//       typeof data.detail === 'string'
//         ? data.detail
//         : typeof data.message === 'string'
//           ? data.message
//           : Array.isArray(data.detail)
//             ? data.detail.map((item: { msg?: string }) => item.msg ?? '').join(', ')
//             : 'Request failed';
//     throw new ApiError(detail, response.status);
//   }

//   return data as T;
// }

// // ─── Auth / profile ───────────────────────────────────────────────────────────

// export interface AuthUserResponse {
//   id?: string;
//   name: string;
//   email: string;
//   role: string;
//   role_id?: number;
//   courier_id?: string;
// }

// export interface LoginResponse {
//   success: boolean;
//   access_token: string;
//   token_type: string;
//   user: AuthUserResponse;
//   message?: string;
// }
// //  ADD THIS (LOGIN FUNCTION)
// export async function login(email: string, password: string): Promise<LoginResponse> {
//   const data = await apiFetch<LoginResponse>('/api/login', {
//     method: 'POST',
//     body: JSON.stringify({ email, password }),
//     auth: false,
//   });

//   //  Store token for future requests
//   if (data.access_token) {
//     setAccessToken(data.access_token);
//   }

//   //  Store user for UI/session
//   if (data.user) {
//     localStorage.setItem('intellisupply_user', JSON.stringify(data.user));
//   }

//   return data;
// }
// export async function fetchCurrentUser(): Promise<AuthUserResponse> {
//   const data = await apiFetch<{ success: boolean; user: AuthUserResponse }>('/api/me');
//   return data.user;
// }

// export async function updateCurrentUser(payload: { name?: string }): Promise<AuthUserResponse> {
//   const data = await apiFetch<{ success: boolean; user: AuthUserResponse }>('/api/me', {
//     method: 'PATCH',
//     body: JSON.stringify(payload),
//   });
//   return data.user;
// }

// export async function googleLogin(idToken: string): Promise<LoginResponse> {
//   const data = await apiFetch<LoginResponse>('/api/google-login', {
//     method: 'POST',
//     body: JSON.stringify({ id_token: idToken }),
//     auth: false,
//   });

//   // ✅ same logic as normal login
//   if (data.access_token) {
//     setAccessToken(data.access_token);
//   }

//   if (data.user) {
//     localStorage.setItem('intellisupply_user', JSON.stringify(data.user));
//   }

//   return data;
// }


// // ─── Shipments ────────────────────────────────────────────────────────────────

// export interface CreateShipmentPayload {
//   from_hub_name: string;
//   to_hub_name: string;
//   delivery_date: string;
//   receipt_time?: string;
//   notes?: string;
// }

// export interface OrderDetail {
//   order_id: string;
//   city_name?: string;
//   ds?: number;
//   delivery_day?: string;
//   receipt_time?: string;
//   from_hub_name?: string;
//   from_lat?: number;
//   from_lon?: number;
//   to_hub_name?: string;
//   to_lat?: number;
//   to_lon?: number;
//   assigned_courier_id?: string;
//   assigned_courier_name?: string;
//   assigned_courier_email?: string;
//   assigned_courier_hub_name?: string;
//   nearest_courier_distance_m?: number;
//   typecode?: string;
//   aoi_id?: string;
//   notes?: string;
// }

// export interface ShipmentListItem {
//   order_id: string;
//   from_hub_name?: string;
//   to_hub_name?: string;
//   city_name?: string;
//   delivery_day?: string;
//   receipt_time?: string;
//   assigned_courier_id?: string;
//   assigned_courier_name?: string;
//   status?: string;
// }

// export interface CreateShipmentResult {
//   success: boolean;
//   message: string;
//   order?: {
//     order_id: string;
//     assigned_courier_id?: string;
//     assigned_courier_name?: string;
//     assigned_courier_hub_name?: string;
//     city_name?: string;
//     delivery_day?: string;
//     receipt_time?: string;
//     from_hub_name?: string;
//     to_hub_name?: string;
//     notes?: string;
//   };
// }

// export async function createShipment(payload: CreateShipmentPayload): Promise<CreateShipmentResult> {
//   return apiFetch<CreateShipmentResult>('/orders/shipments', {
//     method: 'POST',
//     body: JSON.stringify(payload),
//   });
// }

// // ─── Cities / hubs (logistics dropdowns) ─────────────────────────────────────

// export interface CityListItem {
//   city_id?: number;
//   city_name: string;
// }

// export interface HubListItem {
//   hub_id?: number;
//   hub_name: string;
//   city_name?: string;
// }

// export async function listCities(): Promise<CityListItem[]> {
//   const data = await apiFetch<{ cities: CityListItem[] }>('/orders/cities');
//   return data.cities;
// }

// export async function listHubs(cityName: string): Promise<HubListItem[]> {
//   const params = new URLSearchParams({ city_name: cityName });
//   const data = await apiFetch<{ hubs: HubListItem[] }>(`/orders/hubs?${params.toString()}`);
//   return data.hubs;
// }

// export interface ListShipmentsOptions {
//   limit?: number;
//   courierId?: string;
//   deliveryDay?: string;
// }

// export async function listShipments(options: ListShipmentsOptions | number = {}): Promise<ShipmentListItem[]> {
//   // Accept a bare number for backwards-compat (legacy callers pass limit directly)
//   if (typeof options === 'number') {
//     options = { limit: options };
//   }
//   const { limit = 50, courierId, deliveryDay } = options;
//   const params = new URLSearchParams({ limit: String(limit) });
//   if (courierId) params.set('courier_id', courierId);
//   if (deliveryDay) params.set('delivery_day', deliveryDay);
//   const data = await apiFetch<{ shipments: ShipmentListItem[] }>(`/orders/shipments?${params.toString()}`);
//   return data.shipments;
// }

// export async function getShipment(orderId: string): Promise<OrderDetail> {
//   const data = await apiFetch<{ success: boolean; order: OrderDetail }>(
//     `/orders/${encodeURIComponent(orderId)}`,
//   );
//   return data.order;
// }

// // ─── Couriers list ────────────────────────────────────────────────────────────

// export interface CourierListItem {
//   courier_id: string;
//   name: string;
//   hub_name?: string;
//   city_name?: string;
//   email?: string;
//   order_count?: number;
// }

// export async function listCouriers(limit = 200): Promise<CourierListItem[]> {
//   const data = await apiFetch<{ couriers: CourierListItem[] }>(`/couriers?limit=${limit}`);
//   return data.couriers;
// }

// export async function listCouriersWithOrders(
//   deliveryDay: string,
//   limit = 200,
// ): Promise<CourierListItem[]> {
//   const params = new URLSearchParams({
//     limit: String(limit),
//     with_orders_only: 'true',
//     delivery_day: deliveryDay,
//   });
//   const data = await apiFetch<{ couriers: CourierListItem[] }>(`/couriers?${params.toString()}`);
//   return data.couriers;
// }

// // ─── Courier route + ETA ──────────────────────────────────────────────────────

// export interface RouteStop {
//   sequence: number;
//   order_id: string;
//   from_hub_name?: string;
//   to_hub_name?: string;
//   city_name?: string;
//   delivery_day?: string;
//   eta_minutes: number;
//   eta_from_start_minutes: number;
//   estimated_arrival: string;
// }

// export interface CourierRouteResult {
//   courier_id: string;
//   courier_name?: string;
//   delivery_day: string;
//   route_start_time: string;
//   predicted_sequence: string[];
//   stops: RouteStop[];
//   total_eta_minutes: number;
//   source?: 'graphdb' | 'ml_model';
// }

// export async function predictCourierRoute(
//   courierId: 'me' | string,
//   deliveryDay: string,
// ): Promise<CourierRouteResult> {
//   return apiFetch<CourierRouteResult>(`/couriers/${courierId}/route`, {
//     method: 'POST',
//     body: JSON.stringify({ delivery_day: deliveryDay }),
//   });
// }

// // ─── Users ────────────────────────────────────────────────────────────────────

// export interface AdminUserRecord {
//   id: string;
//   name: string;
//   email: string;
//   role: string;
//   account_type?: string;
//   is_active?: boolean;
// }

// export async function listUsers(limit = 100): Promise<AdminUserRecord[]> {
//   const data = await apiFetch<{ users: AdminUserRecord[] }>(`/api/users?limit=${limit}`);
//   return data.users;
// }

// // ─── User registration ────────────────────────────────────────────────────────

// export interface RegisterUserPayload {
//   name: string;
//   email: string;
//   password: string;
//   role: 'logistics_manager' | 'inventory_manager';
// }

// export async function registerUser(payload: RegisterUserPayload): Promise<{ success: boolean; message?: string; user?: object }> {
//   return apiFetch('/api/register', {
//     method: 'POST',
//     body: JSON.stringify(payload),
//   });
// }

// // ─── Courier creation ─────────────────────────────────────────────────────────

// export interface CreateCourierPayload {
//   name: string;
//   email: string;
//   password: string;
//   city_name: string;
//   hub_name: string;
// }

// export async function createCourierFrontend(payload: CreateCourierPayload): Promise<{ success: boolean; message?: string; courier?: object }> {
//   return apiFetch('/couriers', {
//     method: 'POST',
//     body: JSON.stringify(payload),
//   });
// }

// // ─── Inventory ────────────────────────────────────────────────────────────────

// export interface InventoryProduct {
//   id: string;
//   name: string;
//   category?: string;
//   unit_price?: number;
//   supplier_name?: string;
//   stock: number;
//   status: string;
// }

// export interface InventorySummary {
//   on_hand_units: number;
//   warehouse_count: number;
//   product_count: number;
//   stockout_risk_pct: number;
//   demand_coverage_pct: number;
//   reorder_alerts: number;
//   risk_signals: Array<{ title: string; description: string; severity: string }>;
// }

// export async function listInventoryProducts(search = '', category = ''): Promise<InventoryProduct[]> {
//   const params = new URLSearchParams();
//   if (search) params.set('search', search);
//   if (category) params.set('category', category);
//   const data = await apiFetch<{ products: InventoryProduct[] }>(`/inventory/products?${params.toString()}`);
//   return data.products;
// }

// export async function getInventorySummary(): Promise<InventorySummary> {
//   const data = await apiFetch<{ summary: InventorySummary }>('/inventory/summary');
//   return data.summary;
// }

// export async function getInventoryForecastTrend(): Promise<Array<{ period: string; demand: number; inventory: number }>> {
//   const data = await apiFetch<{ trend: Array<{ period: string; demand: number; inventory: number }> }>(
//     '/inventory/forecast-trend',
//   );
//   return data.trend;
// }

// export async function createInventoryProduct(payload: {
//   name: string;
//   category?: string;
//   unit_price?: number;
//   supplier_name?: string;
// }): Promise<InventoryProduct> {
//   const data = await apiFetch<{ product: InventoryProduct }>('/inventory/products', {
//     method: 'POST',
//     body: JSON.stringify(payload),
//   });
//   return data.product;
// }

// export async function updateInventoryProduct(
//   productId: string,
//   payload: { name?: string; category?: string; unit_price?: number; supplier_name?: string },
// ): Promise<InventoryProduct> {
//   const data = await apiFetch<{ product: InventoryProduct }>(`/inventory/products/${productId}`, {
//     method: 'PATCH',
//     body: JSON.stringify(payload),
//   });
//   return data.product;
// }

// export async function deleteInventoryProduct(productId: string): Promise<void> {
//   await apiFetch(`/inventory/products/${productId}`, { method: 'DELETE' });
// }

// // ─── Copilot ──────────────────────────────────────────────────────────────────

// export interface CopilotResponse {
//   status: string;
//   message?: string;
//   question?: string;
//   answer?: string;
//   reason?: string;
//   role?: string;
//   task?: string;
//   source?: string;
//   data?: Record<string, unknown>;
// }

// export async function queryCopilot(
//   query: string,
//   sessions?: {
//     logisticsSession?: Record<string, unknown> | null;
//     inventorySession?: Record<string, unknown> | null;
//   },
// ): Promise<CopilotResponse> {
//   return apiFetch<CopilotResponse>('/copilot/query', {
//     method: 'POST',
//     body: JSON.stringify({
//       query,
//       logistics_session: sessions?.logisticsSession ?? undefined,
//       inventory_session: sessions?.inventorySession ?? undefined,
//     }),
//   });
// }

// // ─── Voice (multilingual mic → English) ───────────────────────────────────────

// export interface VoiceTranscribeResponse {
//   success: boolean;
//   detected_language?: string | null;
//   original_text: string;
//   english_text: string;
//   message?: string | null;
// }

// export async function transcribeVoice(
//   audio: Blob,
//   languageHint: string = 'auto',
// ): Promise<VoiceTranscribeResponse> {
//   const form = new FormData();
//   const ext = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('wav') ? 'wav' : 'webm';
//   form.append('audio', audio, `recording.${ext}`);
//   form.append('language_hint', languageHint);

//   const headers = new Headers();
//   const token = getAccessToken();
//   if (token) {
//     headers.set('Authorization', `Bearer ${token}`);
//   }

//   const response = await fetch(`${API_BASE}/voice/transcribe`, {
//     method: 'POST',
//     body: form,
//     headers,
//     credentials: 'include',
//   });

//   const data = await response.json().catch(() => ({}));

//   if (!response.ok) {
//     const detail =
//       typeof data.detail === 'string'
//         ? data.detail
//         : typeof data.message === 'string'
//           ? data.message
//           : 'Voice transcription failed';
//     throw new ApiError(detail, response.status);
//   }

//   return data as VoiceTranscribeResponse;
// }

// // ─── Dashboard / notifications ──────────────────────────────────────────────────

// export interface DashboardSummary {
//   sales_volume_label: string;
//   sales_volume_value: string;
//   logistics_reliability_pct: number;
//   hardware_uptime_pct: number;
//   active_sessions: number;
//   orders_funnel: number;
//   route_on_time_pct: number;
//   recent_shipments: number;
// }

// export async function getDashboardSummary(): Promise<DashboardSummary> {
//   const data = await apiFetch<{ summary: DashboardSummary }>('/api/dashboard/summary');
//   return data.summary;
// }

// export interface NotificationItem {
//   notification_id: string;
//   title: string;
//   message: string;
//   alert_type: string;
//   severity: string;
//   target_role?: string | null;
//   target_user_id?: string | null;
//   related_entity_type?: string | null;
//   related_entity_id?: string | null;
//   source?: string | null;
//   is_read: boolean;
//   created_at?: string;
// }

// export async function listNotifications(limit = 20): Promise<NotificationItem[]> {
//   const data = await apiFetch<{
//     success: boolean;
//     notifications: NotificationItem[];
//     count: number;
//   }>(`/api/notifications?limit=${limit}`);

//   return data.notifications;
// }

// export async function getUnreadNotificationCount(): Promise<number> {
//   const data = await apiFetch<{
//     success: boolean;
//     unread_count: number;
//   }>('/api/notifications/unread-count');

//   return data.unread_count;
// }

// export async function markNotificationRead(
//   notificationId: string,
// ): Promise<NotificationItem> {
//   const data = await apiFetch<{
//     success: boolean;
//     notification: NotificationItem;
//   }>(`/api/notifications/${notificationId}/read`, {
//     method: 'PATCH',
//   });

//   return data.notification;
// }

// export async function markAllNotificationsRead(): Promise<number> {
//   const data = await apiFetch<{
//     success: boolean;
//     updated_count: number;
//   }>('/api/notifications/read-all', {
//     method: 'PATCH',
//   });

//   return data.updated_count;
// }

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

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
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
    const detail =
      typeof data.detail === 'string'
        ? data.detail
        : typeof data.message === 'string'
        ? data.message
        : Array.isArray(data.detail)
        ? data.detail.map((item: any) => item.msg ?? '').join(', ')
        : 'Request failed';

    throw new ApiError(detail, response.status);
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

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>('/api/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    auth: false,
  });

  if (data.access_token) {
    setAccessToken(data.access_token);
  }

  if (data.user) {
    localStorage.setItem('intellisupply_user', JSON.stringify(data.user));
  }

  return data;
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

// ✅ ✅ FIXED GOOGLE LOGIN
export async function googleLogin(idToken: string, role: string): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>('/api/google-login', {
    method: 'POST',
    body: JSON.stringify({
      id_token: idToken,
      role, // ✅ CRITICAL FIX
    }),
    auth: false,
  });

  if (data.access_token) {
    setAccessToken(data.access_token);
  }

  if (data.user) {
    localStorage.setItem('intellisupply_user', JSON.stringify(data.user));
  }

  return data;
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

// =======================
// ✅ COPILOT
// =======================

export async function queryCopilot(query: string, sessions?: any) {
  return apiFetch('/copilot/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      ...sessions,
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
// ✅ DASHBOARD + NOTIFS
// =======================

export async function getDashboardSummary() {
  const data = await apiFetch<{ summary: any }>('/api/dashboard/summary');
  return data.summary;
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