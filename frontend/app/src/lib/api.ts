const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

export interface CreateShipmentPayload {
  from_hub_name: string;
  to_hub_name: string;
  delivery_date: string;
  ds: number;
  receipt_time?: string;
  notes?: string;
}

export interface RouteStop {
  sequence: number;
  order_id: string;
  lat_wgs84: number;
  lon_wgs84: number;
}

export interface RoutePrediction {
  route_prediction_id: string;
  courier_id: string;
  cluster_id: number;
  city_name: string;
  ds: number;
  delivery_day: string;
  order_ids: string[];
  predicted_sequence: string[];
  stops: RouteStop[];
  stop_count: number;
}

export interface CreateShipmentResult {
  success: boolean;
  message: string;
  order?: {
    order_id: string;
    assigned_courier_id?: string;
    assigned_courier_name?: string;
    city_name?: string;
    delivery_day?: string;
    receipt_time?: string;
    from_hub_name?: string;
    to_hub_name?: string;
    notes?: string;
  };
  route_prediction?: RoutePrediction | null;
  route_error?: string | null;
}

export async function createShipment(
  payload: CreateShipmentPayload,
): Promise<CreateShipmentResult> {
  const response = await fetch(`${API_BASE}/orders/shipments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    const detail =
      typeof data.detail === 'string'
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((item: { msg?: string }) => item.msg ?? '').join(', ')
          : 'Failed to create shipment';
    throw new Error(detail);
  }

  return data as CreateShipmentResult;
}

// ─── User registration ────────────────────────────────────────────────────────

export interface RegisterUserPayload {
  name: string;
  email: string;
  password: string;
  role: 'logistics_manager' | 'inventory_manager';
}

export async function registerUser(payload: RegisterUserPayload): Promise<{ success: boolean; message?: string; user?: object }> {
  const res = await fetch(`${API_BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message ?? 'Registration failed.');
  }
  return data;
}

// ─── Courier creation (uses existing /couriers POST endpoint) ─────────────────

export interface CreateCourierPayload {
  name: string;
  email: string;
  password: string;
  city_name: string;
  hub_name: string;
  ds?: number;
}

export async function createCourierFrontend(payload: CreateCourierPayload): Promise<{ success: boolean; message?: string; courier?: object }> {
  const res = await fetch(`${API_BASE}/couriers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, ds: payload.ds ?? 318 }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail ?? data.message ?? 'Courier creation failed.');
  }
  return data;
}

