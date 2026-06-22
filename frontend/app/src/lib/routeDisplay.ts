import type { CourierRouteResult, CourierStartPoint, RouteStop } from '@/lib/api';

function parseRouteStart(routeStartTime?: string): Date | null {
  if (!routeStartTime) return null;
  const normalized = routeStartTime.includes('T')
    ? routeStartTime
    : routeStartTime.replace(' ', 'T');
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatArrivalTime(date: Date): string {
  return date.toTimeString().slice(0, 5);
}

/** Reverse predicted stop order and recalculate sequence / cumulative ETAs for display. */
export function stopsForDisplay(
  stops: RouteStop[],
  routeStartTime?: string,
): RouteStop[] {
  const reversed = [...stops].reverse();
  const start = parseRouteStart(routeStartTime);
  let cumulative = 0;

  return reversed.map((stop, index) => {
    cumulative += stop.eta_minutes;
    const arrival =
      start != null
        ? formatArrivalTime(new Date(start.getTime() + cumulative * 60_000))
        : stop.estimated_arrival;

    return {
      ...stop,
      sequence: index + 1,
      eta_from_start_minutes: Math.round(cumulative * 10) / 10,
      estimated_arrival: arrival,
    };
  });
}

function buildRoutePathFromStops(
  stops: RouteStop[],
  courierStart?: CourierStartPoint | null,
): [number, number][] {
  const path: [number, number][] = [];
  let last: [number, number] | null = null;

  if (courierStart?.lat != null && courierStart.lng != null) {
    last = [courierStart.lat, courierStart.lng];
    path.push(last);
  }

  for (const stop of stops) {
    const fromPt: [number, number] | null =
      stop.from_lat != null && stop.from_lng != null
        ? [stop.from_lat, stop.from_lng]
        : stop.lat_wgs84 != null && stop.lon_wgs84 != null
          ? [stop.lat_wgs84, stop.lon_wgs84]
          : null;
    const toPt: [number, number] | null =
      stop.to_lat != null && stop.to_lng != null
        ? [stop.to_lat, stop.to_lng]
        : fromPt;

    if (fromPt && (last == null || fromPt[0] !== last[0] || fromPt[1] !== last[1])) {
      path.push(fromPt);
      last = fromPt;
    }
    if (toPt && (last == null || toPt[0] !== last[0] || toPt[1] !== last[1])) {
      path.push(toPt);
      last = toPt;
    }
  }

  return path;
}

/** Present courier routes in forward hub-to-hub order across UI and map. */
export function routeForDisplay(route: CourierRouteResult): CourierRouteResult {
  const stops = stopsForDisplay(route.stops, route.route_start_time);
  return {
    ...route,
    stops,
    predicted_sequence: [...route.predicted_sequence].reverse(),
    path: buildRoutePathFromStops(stops, route.courier_start),
  };
}
