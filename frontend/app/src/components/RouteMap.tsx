import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  TrendingUp,
  Route as RouteIcon,
  AlertTriangle,
  Layers,
  Sparkles,
  Truck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { locations, routes, statsCards, aiInsights } from '@/data/mockData';
import { predictCourierRoute, type CourierRouteResult, type HubMapLocation } from '@/lib/api';
import { fetchRoadLegs, fetchRoadRoute } from '@/lib/roadRouting';
import type { Route } from '@/data/mockData';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

const createCustomIcon = (type: string, isSelected: boolean) => {
  const colors: Record<string, string> = {
    warehouse: 'bg-blue-500',
    supplier: 'bg-amber-500',
    customer: 'bg-emerald-500',
    port: 'bg-indigo-500',
    hub: 'bg-violet-500',
  };
  const color = colors[type] || 'bg-slate-500';
  const border = isSelected ? 'ring-2 ring-primary ring-offset-2 border-white' : 'border-white';

  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="w-4.5 h-4.5 ${color} ${border} rounded-full border-2 shadow-lg transition-all" style="width: 18px; height: 18px;"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -12],
  });
};

const STOP_PALETTE = [
  { bg: 'linear-gradient(135deg,#059669,#10b981)', ring: '#a7f3d0', shadow: 'rgba(5,150,105,0.45)' },
  { bg: 'linear-gradient(135deg,#2563eb,#3b82f6)', ring: '#bfdbfe', shadow: 'rgba(37,99,235,0.45)' },
  { bg: 'linear-gradient(135deg,#7c3aed,#8b5cf6)', ring: '#ddd6fe', shadow: 'rgba(124,58,237,0.45)' },
  { bg: 'linear-gradient(135deg,#db2777,#ec4899)', ring: '#fbcfe8', shadow: 'rgba(219,39,119,0.45)' },
  { bg: 'linear-gradient(135deg,#d97706,#f59e0b)', ring: '#fde68a', shadow: 'rgba(217,119,6,0.45)' },
];

const createStopIcon = (sequence: number, highlighted: boolean) => {
  const palette = STOP_PALETTE[(sequence - 1) % STOP_PALETTE.length];
  const size = highlighted ? 40 : 34;
  const anchor = size / 2;

  return L.divIcon({
    className: 'courier-stop-marker',
    html: `<div class="courier-stop-pin${highlighted ? ' courier-stop-pin--active' : ''}" style="
      width:${size}px;height:${size}px;
      background:${palette.bg};
      box-shadow:0 4px 14px ${palette.shadow}${highlighted ? `,0 0 0 4px ${palette.ring}` : ''};
    ">
      <span>${sequence}</span>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [anchor, anchor],
    popupAnchor: [0, -anchor],
  });
};

const createCourierStartIcon = () =>
  L.divIcon({
    className: 'courier-start-marker',
    html: `<div class="courier-start-pin">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 17h4"/><path d="M2 9h12v8H2z"/><path d="M14 9h5l2 4v4h-7V9z"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>
      </svg>
    </div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });

const CHINA_CENTER: [number, number] = [35.0, 105.0];
const CHINA_ZOOM = 5;
const CHINA_BOUNDS = L.latLngBounds([18.0, 73.5], [53.5, 135.0]);

function MapBounds({ bounds }: { bounds: L.LatLngBounds }) {
  const map = useMap();
  useEffect(() => {
    map.setMaxBounds(bounds);
    map.options.minZoom = 4;
  }, [map, bounds]);
  return null;
}
function MapFitter({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [72, 72], maxZoom: 12 });
  }, [map, points]);
  return null;
}

function stopLegPoints(stop: CourierRouteResult['stops'][number]): [number, number][] {
  const leg: [number, number][] = [];
  if (stop.from_lat != null && stop.from_lng != null) {
    leg.push([stop.from_lat, stop.from_lng]);
  }
  if (stop.to_lat != null && stop.to_lng != null) {
    leg.push([stop.to_lat, stop.to_lng]);
  }
  if (!leg.length && stop.lat_wgs84 != null && stop.lon_wgs84 != null) {
    leg.push([stop.lat_wgs84, stop.lon_wgs84]);
  }
  return leg;
}

function stopPopupHtml(stop: CourierRouteResult['stops'][number], highlighted: boolean) {
  const palette = STOP_PALETTE[(stop.sequence - 1) % STOP_PALETTE.length];
  return `
    <div class="courier-popup">
      <div class="courier-popup__badge" style="background:${palette.bg}">Stop ${stop.sequence}</div>
      <p class="courier-popup__title">${stop.order_id}</p>
      <p class="courier-popup__route">${stop.from_hub_name ?? 'Origin'} → ${stop.to_hub_name ?? 'Destination'}</p>
      <div class="courier-popup__meta">
        <span>${stop.eta_minutes} min leg</span>
        <span>${stop.estimated_arrival ?? '—'}</span>
      </div>
      ${highlighted ? '<p class="courier-popup__highlight">Selected shipment</p>' : ''}
    </div>
  `;
}

function stopMarkerPosition(stop: CourierRouteResult['stops'][number]): [number, number] | null {
  const leg = stopLegPoints(stop);
  return leg.length ? leg[leg.length - 1] : null;
}

interface RouteMapProps {
  selectedRouteId?: string | null;
  onRouteSelect?: (routeId: string) => void;
  activeCourierRoute?: CourierRouteResult | null;
  highlightedOrderId?: string | null;
  onStopSelect?: (orderId: string) => void;
  showDemoRoutes?: boolean;
  hubLocations?: HubMapLocation[];
  chinaMapOnly?: boolean;
}

export default function RouteMap({
  selectedRouteId,
  onRouteSelect,
  activeCourierRoute = null,
  highlightedOrderId = null,
  onStopSelect,
  showDemoRoutes,
  hubLocations = [],
  chinaMapOnly = false,
}: RouteMapProps) {
  const [showDelays, setShowDelays] = useState(true);
  const [showAISuggestions, setShowAISuggestions] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const [mapObject, setMapObject] = useState<L.Map | null>(null);

  const demoMode = showDemoRoutes ?? !activeCourierRoute;
  const hubMapMode = chinaMapOnly || hubLocations.length > 0;
  const showMockDemo = demoMode && !hubMapMode;

  const livePath = useMemo<[number, number][]>(() => {
    if (!activeCourierRoute?.path?.length) return [];
    return activeCourierRoute.path
      .filter((pt) => pt.length === 2 && pt[0] != null && pt[1] != null)
      .map((pt) => [pt[0], pt[1]] as [number, number]);
  }, [activeCourierRoute]);

  const highlightLeg = useMemo<[number, number][]>(() => {
    if (!activeCourierRoute || !highlightedOrderId) return [];
    const stop = activeCourierRoute.stops.find((s) => s.order_id === highlightedOrderId);
    return stop ? stopLegPoints(stop) : [];
  }, [activeCourierRoute, highlightedOrderId]);

  const routeLegs = useMemo(() => {
    if (!activeCourierRoute?.stops?.length) return [];
    return activeCourierRoute.stops
      .map((stop) => ({
        orderId: stop.order_id,
        sequence: stop.sequence,
        points: stopLegPoints(stop),
      }))
      .filter((leg) => leg.points.length >= 2);
  }, [activeCourierRoute]);

  const [mlRoute, setMlRoute] = useState<CourierRouteResult | null>(null);
  const [roadLegPaths, setRoadLegPaths] = useState<Record<string, [number, number][]>>({});
  const [roadLivePath, setRoadLivePath] = useState<[number, number][]>([]);
  const [roadRouting, setRoadRouting] = useState(false);

  const displayLegPoints = useCallback(
    (orderId: string, fallback: [number, number][]) =>
      roadLegPaths[orderId]?.length ? roadLegPaths[orderId] : fallback,
    [roadLegPaths],
  );

  const displayLivePath = useMemo(
    () => (roadLivePath.length >= 2 ? roadLivePath : livePath),
    [roadLivePath, livePath],
  );

  const displayHighlightLeg = useMemo(() => {
    if (!highlightedOrderId) return highlightLeg;
    const detailed = roadLegPaths[highlightedOrderId];
    return detailed?.length ? detailed : highlightLeg;
  }, [highlightedOrderId, highlightLeg, roadLegPaths]);

  const fitPoints = useMemo<[number, number][]>(() => {
    if (displayHighlightLeg.length >= 2) return displayHighlightLeg;
    if (displayLivePath.length) return displayLivePath;
    if (hubMapMode && demoMode) return [];
    if (!demoMode) return [];
    return locations.map((l) => [l.lat, l.lng] as [number, number]);
  }, [displayHighlightLeg, displayLivePath, demoMode, hubMapMode]);

  const mapCenter: [number, number] = hubMapMode ? CHINA_CENTER : [15.5, 78.5];
  const mapZoom = hubMapMode ? CHINA_ZOOM : 6;

  useEffect(() => {
    if (!activeCourierRoute) {
      setRoadLegPaths({});
      setRoadLivePath([]);
      setRoadRouting(false);
      return;
    }

    let cancelled = false;
    setRoadRouting(true);

    void (async () => {
      try {
        if (routeLegs.length > 0) {
          const result = await fetchRoadLegs(routeLegs, livePath);
          if (!cancelled) {
            setRoadLegPaths(result.legs);
            setRoadLivePath(result.fullPath);
          }
          return;
        }

        if (livePath.length >= 2) {
          const detailed = await fetchRoadRoute(livePath);
          if (!cancelled) {
            setRoadLegPaths({});
            setRoadLivePath(detailed);
          }
          return;
        }

        if (!cancelled) {
          setRoadLegPaths({});
          setRoadLivePath([]);
        }
      } finally {
        if (!cancelled) {
          setRoadRouting(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeCourierRoute, routeLegs, livePath]);

  const visibleStats = useMemo(
    () => statsCards.filter((stat) => stat.label !== 'Avg ETA' && stat.label !== 'Fuel Efficiency'),
    [],
  );

  const routeColor = useCallback(
    (route: Route) => {
      if (route.id === selectedRouteId) return '#3B82F6';
      if (route.status === 'critical') return '#EF4444';
      if (route.status === 'delayed') return '#F59E0B';
      if (route.status === 'optimized') return '#3B82F6';
      return '#10B981';
    },
    [selectedRouteId],
  );

  const routeWeight = useCallback(
    (route: Route) => (route.id === selectedRouteId ? 5 : 3),
    [selectedRouteId],
  );

  const routeOpacity = useCallback(
    (route: Route) => {
      if (!selectedRouteId) return 0.85;
      return route.id === selectedRouteId ? 1 : 0.3;
    },
    [selectedRouteId],
  );

  const filteredRoutes = useMemo(() => {
    let result = routes;
    if (!showDelays) {
      result = result.filter((r) => r.status !== 'delayed' && r.status !== 'critical');
    }
    return result;
  }, [showDelays]);

  const handlePredictRoute = async (route: Route) => {
    onRouteSelect?.(route.id);
    const today = new Date().toISOString().slice(0, 10);
    const courierId = (route.driver && String(route.driver)) || 'me';
    try {
      const res = await predictCourierRoute(courierId === 'me' ? 'me' : courierId, today);
      setMlRoute(res);
    } catch (err) {
      console.warn('Route prediction failed', err);
      setMlRoute(null);
    }
  };

  useEffect(() => {
    if (!mapObject) return;
    mapObject.invalidateSize();
  }, [mapObject, activeCourierRoute]);

  return (
    <div className="relative h-full min-h-0 overflow-hidden bg-gradient-to-br from-slate-100 via-sky-50/40 to-slate-100">
      <div className="absolute inset-0 grid-bg opacity-25 pointer-events-none z-[1]" />
      <div className="pointer-events-none absolute inset-0 z-[2] bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(15,23,42,0.06)_100%)]" />

      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        scrollWheelZoom
        className="h-full w-full min-h-0"
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
        maxBounds={hubMapMode ? CHINA_BOUNDS : undefined}
        maxBoundsViscosity={hubMapMode ? 1.0 : undefined}
        ref={(mapInstance) => {
          if (mapInstance && !mapObject) {
            setMapObject(mapInstance);
            mapInstance.invalidateSize();
            setMapReady(true);
          }
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        {hubMapMode && <MapBounds bounds={CHINA_BOUNDS} />}
        {fitPoints.length > 0 && <MapFitter points={fitPoints} />}

        {hubMapMode &&
          hubLocations.map((hub) => (
            <Marker
              key={String(hub.hub_id)}
              position={[hub.lat, hub.lng]}
              icon={createCustomIcon('hub', false)}
            >
              <Popup>
                <div className="text-xs">
                  <p className="font-semibold text-sm">{hub.hub_name}</p>
                  {hub.city_name && (
                    <p className="text-muted-foreground mt-0.5">{hub.city_name}</p>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}

        {showMockDemo &&
          locations.map((loc) => (
            <Marker key={loc.id} position={[loc.lat, loc.lng]} icon={createCustomIcon(loc.type, false)}>
              <Popup>
                <div className="text-xs">
                  <p className="font-semibold text-sm">{loc.name}</p>
                </div>
              </Popup>
            </Marker>
          ))}

        {showMockDemo &&
          filteredRoutes.map((route) => (
            <Polyline
              key={route.id}
              positions={
                route.waypoints || [
                  [route.origin.lat, route.origin.lng],
                  [route.destination.lat, route.destination.lng],
                ]
              }
              pathOptions={{
                color: routeColor(route),
                weight: routeWeight(route),
                opacity: routeOpacity(route),
                dashArray: route.routeType === 'alternate' ? '8 6' : undefined,
                className:
                  route.status === 'delayed' || route.status === 'critical' ? 'animate-dash' : '',
              }}
              eventHandlers={{
                click: () => {
                  onRouteSelect?.(route.id);
                  void handlePredictRoute(route);
                },
              }}
            />
          ))}

        {activeCourierRoute && routeLegs.length > 0 && (
          <>
            {routeLegs.map((leg) => {
              const isHighlighted = leg.orderId === highlightedOrderId;
              const dimmed = Boolean(highlightedOrderId) && !isHighlighted;
              const positions = displayLegPoints(leg.orderId, leg.points);
              return (
                <Polyline
                  key={`leg-shadow-${leg.orderId}`}
                  positions={positions}
                  pathOptions={{
                    color: '#ffffff',
                    weight: isHighlighted ? 12 : 8,
                    opacity: dimmed ? 0.35 : 0.85,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                />
              );
            })}
            {routeLegs.map((leg) => {
              const isHighlighted = leg.orderId === highlightedOrderId;
              const dimmed = Boolean(highlightedOrderId) && !isHighlighted;
              const positions = displayLegPoints(leg.orderId, leg.points);
              return (
                <Polyline
                  key={`leg-${leg.orderId}`}
                  positions={positions}
                  pathOptions={{
                    color: isHighlighted ? '#f59e0b' : '#0ea5e9',
                    weight: isHighlighted ? 7 : 5,
                    opacity: dimmed ? 0.28 : isHighlighted ? 1 : 0.92,
                    lineCap: 'round',
                    lineJoin: 'round',
                    className: isHighlighted ? 'courier-leg-highlight' : 'courier-leg-flow',
                    dashArray: dimmed ? '6 10' : undefined,
                  }}
                />
              );
            })}
          </>
        )}

        {activeCourierRoute && routeLegs.length === 0 && displayLivePath.length > 1 && (
          <>
            <Polyline
              positions={displayLivePath}
              pathOptions={{
                color: '#ffffff',
                weight: 10,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            <Polyline
              positions={displayLivePath}
              pathOptions={{
                color: '#0ea5e9',
                weight: 6,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'courier-leg-flow',
              }}
            />
          </>
        )}

        {activeCourierRoute?.courier_start && (
          <Marker
            position={[activeCourierRoute.courier_start.lat, activeCourierRoute.courier_start.lng]}
            icon={createCourierStartIcon()}
          >
            <Popup>
              <div className="courier-popup">
                <div className="courier-popup__badge courier-popup__badge--start">Start</div>
                <p className="courier-popup__title">
                  {activeCourierRoute.courier_name ?? activeCourierRoute.courier_id}
                </p>
                <p className="courier-popup__route">Courier departure hub</p>
              </div>
            </Popup>
          </Marker>
        )}

        {activeCourierRoute?.stops.map((stop) => {
          const position = stopMarkerPosition(stop);
          if (!position) return null;
          const highlighted = stop.order_id === highlightedOrderId;
          return (
            <Marker
              key={stop.order_id}
              position={position}
              icon={createStopIcon(stop.sequence, highlighted)}
              eventHandlers={{
                click: () => onStopSelect?.(stop.order_id),
              }}
            >
              <Popup>
                <div dangerouslySetInnerHTML={{ __html: stopPopupHtml(stop, highlighted) }} />
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

        {/* ML Predicted Route Panel */}
        {mlRoute && (
          <div className="absolute top-20 right-3 z-[30] w-80 rounded-xl border border-border bg-white p-3 shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-xs text-muted-foreground">Predicted route</p>
                <p className="font-semibold">{mlRoute.courier_name ?? mlRoute.courier_id} — {mlRoute.delivery_day}</p>
              </div>
              <button className="text-xs text-muted-foreground" onClick={() => setMlRoute(null)}>Close</button>
            </div>
            <div className="text-sm text-muted-foreground max-h-60 overflow-auto">
              <p className="text-xs mb-1">Sequence</p>
              <ol className="list-decimal list-inside space-y-1">
                {mlRoute.predicted_sequence.map((oid) => (
                  <li key={oid} className="text-[13px]">{oid}</li>
                ))}
              </ol>
            </div>
          </div>
        )}

      {!mapReady && (
        <div className="absolute inset-0 z-[10] flex items-center justify-center bg-white/80">
          <div className="inline-flex items-center gap-2 rounded-3xl border border-border bg-white px-4 py-3 shadow-lg">
            <div className="h-3 w-3 animate-pulse rounded-full bg-primary" />
            <span className="text-sm font-medium text-foreground">Loading map...</span>
          </div>
        </div>
      )}

      {activeCourierRoute && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-3 left-3 z-[20] max-w-[300px] overflow-hidden rounded-2xl border border-white/60 bg-white/90 shadow-xl shadow-sky-100/50 backdrop-blur-md"
        >
          <div className="h-1 bg-gradient-to-r from-sky-500 via-blue-500 to-violet-500" />
          <div className="p-3.5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 text-white shadow-md">
                <Truck className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {activeCourierRoute.courier_name ?? activeCourierRoute.courier_id}
                </p>
                <p className="text-[11px] text-slate-500">{activeCourierRoute.delivery_day}</p>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-1.5">
              <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[10px] font-semibold text-sky-700">
                {activeCourierRoute.stops.length} stops
              </span>
              <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-semibold text-violet-700">
                {activeCourierRoute.total_eta_minutes} min ETA
              </span>
              <span
                className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
                  activeCourierRoute.source === 'graphdb'
                    ? 'bg-emerald-50 text-emerald-700'
                    : activeCourierRoute.source === 'graph_built'
                      ? 'bg-teal-50 text-teal-700'
                      : 'bg-amber-50 text-amber-700'
                }`}
              >
                {activeCourierRoute.source === 'graphdb'
                  ? 'Aura route'
                  : activeCourierRoute.source === 'graph_built'
                    ? 'Graph route'
                    : 'ML predicted'}
              </span>
              {roadRouting ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                  Snapping to roads…
                </span>
              ) : (
                <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[10px] font-semibold text-indigo-700">
                  Road path
                </span>
              )}
            </div>

            <div className="mt-3 flex items-center gap-1">
              {activeCourierRoute.stops.map((stop) => {
                const active = stop.order_id === highlightedOrderId;
                const palette = STOP_PALETTE[(stop.sequence - 1) % STOP_PALETTE.length];
                return (
                  <button
                    key={stop.order_id}
                    type="button"
                    onClick={() => onStopSelect?.(stop.order_id)}
                    className={`flex h-7 min-w-[1.75rem] items-center justify-center rounded-lg text-[11px] font-bold text-white transition-transform ${
                      active ? 'scale-110 ring-2 ring-offset-1' : 'opacity-80 hover:opacity-100'
                    }`}
                    style={{
                      background: palette.bg,
                      ...(active ? { boxShadow: `0 0 0 2px ${palette.ring}` } : {}),
                    }}
                    title={stop.order_id}
                  >
                    {stop.sequence}
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}

      {activeCourierRoute && (
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          className="absolute bottom-3 right-3 z-[20] rounded-xl border border-white/60 bg-white/90 px-3 py-2.5 shadow-lg backdrop-blur-md"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Map legend</p>
          <div className="mt-2 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="h-1 w-5 rounded-full bg-sky-500" style={{ borderRadius: 9999 }} />
              <span className="text-[10px] text-slate-600">Road-following route</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-1 w-5 rounded-full bg-amber-500" />
              <span className="text-[10px] text-slate-600">Selected shipment</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-[8px] font-bold text-white">
                S
              </span>
              <span className="text-[10px] text-slate-600">Courier start</span>
            </div>
          </div>
        </motion.div>
      )}

      {hubMapMode && demoMode && hubLocations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-3 left-3 z-[20] rounded-xl border border-white/60 bg-white/90 px-3 py-2.5 shadow-lg backdrop-blur-md"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            China hub network
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {hubLocations.length} operational hubs
          </p>
        </motion.div>
      )}

      {showMockDemo && (
        <>
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="absolute top-3 left-1/2 z-[20] flex -translate-x-1/2 items-center gap-1.5 rounded-xl border border-border bg-card/95 px-2 py-1.5 shadow-lg backdrop-blur-sm"
          >
            <Button size="sm" variant="ghost" className="h-7 text-[11px] gap-1">
              <RouteIcon className="w-3 h-3" />
              Optimize
            </Button>
            <Button
              size="sm"
              variant={showDelays ? 'secondary' : 'ghost'}
              className="h-7 text-[11px] gap-1"
              onClick={() => setShowDelays(!showDelays)}
            >
              <AlertTriangle className="w-3 h-3" />
              Delays
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-[11px] gap-1"
              onClick={() => setShowLegend(!showLegend)}
            >
              <Layers className="w-3 h-3" />
              Layers
            </Button>
            <Button
              size="sm"
              variant={showAISuggestions ? 'default' : 'ghost'}
              className="h-7 text-[11px] gap-1"
              onClick={() => setShowAISuggestions(!showAISuggestions)}
            >
              <Sparkles className="w-3 h-3" />
              AI
            </Button>
          </motion.div>

          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
              className="absolute top-14 left-3 z-[20] space-y-2"
            >
              {visibleStats.map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 + i * 0.1, duration: 0.3 }}
                  className="bg-card/95 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md border border-border min-w-[130px]"
                >
                  <p className="text-[10px] text-muted-foreground">{stat.label}</p>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{stat.value}</span>
                    <span
                      className={`text-[10px] font-medium ${stat.positive ? 'text-emerald-500' : 'text-red-500'}`}
                    >
                      {stat.change}
                    </span>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </AnimatePresence>

          <AnimatePresence>
            {showAISuggestions && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ delay: 0.7, duration: 0.4 }}
                className="absolute bottom-3 left-3 z-[20] max-w-[280px]"
              >
                <div className="bg-card/95 backdrop-blur-sm rounded-xl shadow-lg border border-border p-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-semibold">AI Insights</span>
                  </div>
                  <div className="space-y-1.5">
                    {aiInsights.map((insight, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 + i * 0.15 }}
                        className="flex items-start gap-1.5"
                      >
                        <TrendingUp className="w-3 h-3 text-primary shrink-0 mt-0.5" />
                        <p className="text-[10px] text-muted-foreground leading-relaxed">{insight}</p>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {showLegend && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: 0.5, duration: 0.4 }}
                className="absolute bottom-3 right-3 z-[20]"
              >
                <div className="bg-card/95 backdrop-blur-sm rounded-xl shadow-lg border border-border p-3 min-w-[160px]">
                  <p className="text-[10px] font-semibold mb-2">Route Legend</p>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-0.5 bg-emerald-500 rounded" />
                      <span className="text-[10px] text-muted-foreground">On Time</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-0.5 bg-amber-500 rounded" />
                      <span className="text-[10px] text-muted-foreground">Delayed</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-0.5 bg-red-500 rounded" />
                      <span className="text-[10px] text-muted-foreground">Critical</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-0.5 bg-blue-500 rounded" />
                      <span className="text-[10px] text-muted-foreground">Live courier route</span>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-border">
                    <p className="text-[10px] font-semibold mb-1.5">Locations</p>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 bg-violet-500 rounded-full border border-white shadow-sm" />
                        <span className="text-[10px] text-muted-foreground">Hub</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
