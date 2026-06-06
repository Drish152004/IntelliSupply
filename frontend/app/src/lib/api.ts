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
