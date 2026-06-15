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
  Warehouse,
  Ship,
  Building2,
  MapPin,
  TrendingUp,
  Route as RouteIcon,
  AlertTriangle,
  Layers,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { locations, routes, statsCards, aiInsights } from '@/data/mockData';
import { predictCourierRoute, type CourierRouteResult } from '@/lib/api';
import type { Route } from '@/data/mockData';

// Fix Leaflet default icon
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

// Custom marker icons using div icons
const createCustomIcon = (type: string, isSelected: boolean) => {
  const colors: Record<string, string> = {
    warehouse: 'bg-blue-500',
    supplier: 'bg-amber-500',
    customer: 'bg-emerald-500',
    port: 'bg-indigo-500',
    hub: 'bg-violet-500',
  };
  const color = colors[type] || 'bg-slate-500';
  const border = isSelected ? 'ring-2 ring-primary ring-offset-2' : '';

  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="w-8 h-8 ${color} ${border} rounded-lg flex items-center justify-center shadow-lg transition-all">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        ${type === 'warehouse' ? '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>' : ''}
        ${type === 'port' ? '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>' : ''}
        ${type === 'supplier' ? '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>' : ''}
        ${type === 'customer' ? '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>' : ''}
        ${type === 'hub' ? '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>' : ''}
      </svg>
    </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

// Map bounds fitter
function MapFitter() {
  const map = useMap();
  useEffect(() => {
    if (!locations.length) return;
    const bounds = L.latLngBounds(locations.map((l) => [l.lat, l.lng]));
    map.fitBounds(bounds, { padding: [60, 60] });
  }, [map]);
  return null;
}

interface RouteMapProps {
  selectedRouteId?: string | null;
  onRouteSelect?: (routeId: string) => void;
}

export default function RouteMap({ selectedRouteId, onRouteSelect }: RouteMapProps) {
  const [showDelays, setShowDelays] = useState(true);
  const [showAISuggestions, setShowAISuggestions] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [mapReady, setMapReady] = useState(false);

  const visibleStats = useMemo(
    () => statsCards.filter((stat) => stat.label !== 'Avg ETA' && stat.label !== 'Fuel Efficiency'),
    []
  );

  const routeColor = useCallback((route: Route) => {
    if (route.id === selectedRouteId) return '#3B82F6';
    if (route.status === 'critical') return '#EF4444';
    if (route.status === 'delayed') return '#F59E0B';
    if (route.status === 'optimized') return '#3B82F6';
    return '#10B981';
  }, [selectedRouteId]);

  const routeWeight = useCallback((route: Route) => {
    return route.id === selectedRouteId ? 5 : 3;
  }, [selectedRouteId]);

  const routeOpacity = useCallback((route: Route) => {
    if (!selectedRouteId) return 0.85;
    return route.id === selectedRouteId ? 1 : 0.3;
  }, [selectedRouteId]);

  const filteredRoutes = useMemo(() => {
    let result = routes;
    if (!showDelays) {
      result = result.filter((r) => r.status !== 'delayed' && r.status !== 'critical');
    }
    return result;
  }, [showDelays]);

  const handleRouteClick = (routeId: string) => {
    onRouteSelect?.(routeId);
  };

  const [mlRoute, setMlRoute] = useState<CourierRouteResult | null>(null);

  const handlePredictRoute = async (route: Route) => {
    onRouteSelect?.(route.id);
    const today = new Date().toISOString().slice(0, 10);
    const courierId = (route.driver && String(route.driver)) || 'me';
    try {
      const res = await predictCourierRoute(courierId === 'me' ? 'me' : courierId, today);
      setMlRoute(res);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('Route prediction failed', err);
      setMlRoute(null);
    }
  };

  const [mapObject, setMapObject] = useState<L.Map | null>(null);

  useEffect(() => {
    if (!mapObject) return;
    mapObject.invalidateSize();
  }, [mapObject]);

  return (
    <div className="relative h-full min-h-0 overflow-hidden bg-slate-100">
      {/* Grid Background Overlay */}
      <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none z-[1]" />

      {/* Map */}
      <MapContainer
        center={[15.5, 78.5]}
        zoom={6}
        scrollWheelZoom={true}
        className="h-full w-full min-h-0"
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
        ref={(mapInstance) => {
          if (mapInstance && !mapObject) {
            setMapObject(mapInstance);
            mapInstance.invalidateSize();
            setMapReady(true);
          }
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapFitter />

        {/* Location Markers */}
        {locations.map((loc) => (
          <Marker
            key={loc.id}
            position={[loc.lat, loc.lng]}
            icon={createCustomIcon(loc.type, false)}
          >
            <Popup>
              <div className="text-xs">
                <p className="font-semibold text-sm">{loc.name}</p>
                <p className="text-muted-foreground capitalize mt-0.5">{loc.type}</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Route Polylines */}
        {filteredRoutes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.waypoints || [[route.origin.lat, route.origin.lng], [route.destination.lat, route.destination.lng]]}
            pathOptions={{
              color: routeColor(route),
              weight: routeWeight(route),
              opacity: routeOpacity(route),
              dashArray: route.routeType === 'alternate' ? '8 6' : undefined,
              className: route.status === 'delayed' || route.status === 'critical' ? 'animate-dash' : '',
            }}
            eventHandlers={{
              click: () => handlePredictRoute(route),
            }}
          >
            <Popup>
              <div className="text-xs min-w-[200px]">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-semibold text-sm">{route.id}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                    route.status === 'ontime' ? 'status-ontime' :
                    route.status === 'delayed' ? 'status-delayed' :
                    route.status === 'critical' ? 'status-critical' :
                    'status-optimized'
                  }`}>
                    {route.status}
                  </span>
                </div>
                <div className="space-y-1 text-muted-foreground">
                  <p><span className="font-medium text-foreground">Driver:</span> {route.driver}</p>
                  <p><span className="font-medium text-foreground">ETA:</span> {route.eta}</p>
                  <p><span className="font-medium text-foreground">Delay Risk:</span> {route.delayRisk}%</p>
                  <p><span className="font-medium text-foreground">Fuel:</span> {route.fuelEstimate}</p>
                  <p><span className="font-medium text-foreground">Cargo:</span> {route.cargoType}</p>
                  <p><span className="font-medium text-foreground">Vehicle:</span> {route.vehicleType}</p>
                </div>
              </div>
            </Popup>
          </Polyline>
        ))}
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

      {/* Top Floating Controls */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4 }}
        className="absolute top-3 left-1/2 z-[20] flex -translate-x-1/2 items-center gap-1.5 rounded-xl border border-border bg-card/95 px-2 py-1.5 shadow-lg backdrop-blur-sm"
      >
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-[11px] gap-1"
          onClick={() => {}}
        >
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

      {/* Floating Stats Cards */}
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
                <span className={`text-[10px] font-medium ${stat.positive ? 'text-emerald-500' : 'text-red-500'}`}>
                  {stat.change}
                </span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>

      {/* AI Insights Panel */}
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

      {/* Bottom Right Legend */}
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
                  <span className="text-[10px] text-muted-foreground">Optimized</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 border-t border-dashed border-slate-400" />
                  <span className="text-[10px] text-muted-foreground">Alternate</span>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-border">
                <p className="text-[10px] font-semibold mb-1.5">Locations</p>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Warehouse className="w-3 h-3 text-black" />
                    <span className="text-[10px] text-muted-foreground">Warehouse</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Ship className="w-3 h-3 text-black" />
                    <span className="text-[10px] text-muted-foreground">Port</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Building2 className="w-3 h-3 text-black" />
                    <span className="text-[10px] text-muted-foreground">Supplier</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3 h-3 text-black" />
                    <span className="text-[10px] text-muted-foreground">Customer</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
