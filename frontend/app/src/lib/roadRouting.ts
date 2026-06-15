/** Fetch road-following geometry via the public OSRM routing service (OpenStreetMap). */

const OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving';
const routeCache = new Map<string, [number, number][]>();

function cacheKey(points: [number, number][]): string {
  return points.map(([lat, lng]) => `${lat.toFixed(5)},${lng.toFixed(5)}`).join('|');
}

function dedupePoints(points: [number, number][]): [number, number][] {
  const out: [number, number][] = [];
  for (const pt of points) {
    const prev = out[out.length - 1];
    if (!prev || prev[0] !== pt[0] || prev[1] !== pt[1]) {
      out.push(pt);
    }
  }
  return out;
}

/**
 * Return a detailed road path between ordered waypoints (lat, lng).
 * Falls back to straight-line points if routing fails.
 */
export async function fetchRoadRoute(
  points: [number, number][],
): Promise<[number, number][]> {
  const waypoints = dedupePoints(
    points.filter(
      (pt) => pt.length === 2 && Number.isFinite(pt[0]) && Number.isFinite(pt[1]),
    ),
  );

  if (waypoints.length < 2) {
    return waypoints;
  }

  const key = cacheKey(waypoints);
  const cached = routeCache.get(key);
  if (cached) {
    return cached;
  }

  const coordPath = waypoints.map(([lat, lng]) => `${lng},${lat}`).join(';');
  const url = `${OSRM_BASE}/${coordPath}?overview=full&geometries=geojson&steps=false`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      return waypoints;
    }

    const data = (await response.json()) as {
      code?: string;
      routes?: Array<{ geometry?: { coordinates?: [number, number][] } }>;
    };

    const coordinates = data.routes?.[0]?.geometry?.coordinates;
    if (data.code !== 'Ok' || !coordinates?.length) {
      return waypoints;
    }

    const roadPath = coordinates.map(([lng, lat]) => [lat, lng] as [number, number]);
    routeCache.set(key, roadPath);
    return roadPath;
  } catch {
    return waypoints;
  }
}

/** Resolve each leg and optional full path in parallel. */
export async function fetchRoadLegs(
  legs: Array<{ orderId: string; points: [number, number][] }>,
  fullPath: [number, number][] = [],
): Promise<{ legs: Record<string, [number, number][]>; fullPath: [number, number][] }> {
  const legResults = await Promise.all(
    legs.map(async (leg) => ({
      orderId: leg.orderId,
      path: await fetchRoadRoute(leg.points),
    })),
  );

  const legsMap: Record<string, [number, number][]> = {};
  for (const entry of legResults) {
    legsMap[entry.orderId] = entry.path;
  }

  const resolvedFull =
    fullPath.length >= 2 ? await fetchRoadRoute(fullPath) : fullPath;

  return { legs: legsMap, fullPath: resolvedFull };
}
