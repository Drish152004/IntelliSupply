import { useEffect, useState } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import {
  listShipments,
  predictCourierRoute,
  listHubLocations,
  type ShipmentListItem,
  type CourierRouteResult,
  type HubMapLocation,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Calendar,
  Loader2,
  AlertCircle,
  Truck,
  ShieldCheck,
  Route as RouteIcon,
  MapPin,
} from 'lucide-react';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Courier() {
  const { user, loading: authLoading } = useAuth();

  const [shipments, setShipments] = useState<ShipmentListItem[]>([]);
  const [shipmentsLoading, setShipmentsLoading] = useState(false);
  const [deliveryDay, setDeliveryDay] = useSessionStorageState('courier_delivery_day', todayISO());

  const [routeResult, setRouteResult] = useState<CourierRouteResult | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);

  const [hubLocations, setHubLocations] = useState<HubMapLocation[]>([]);
  const [highlightedOrderId, setHighlightedOrderId] = useSessionStorageState<string | null>('courier_highlighted_order_id', null);
  const [selectedRouteId, setSelectedRouteId] = useSessionStorageState<string | null>('courier_selected_route_id', null);

  const [mapMessage, setMapMessage] = useState<string | null>(null);

  const [showWeather, setShowWeather] = useState(false);
  const [weatherData, setWeatherData] = useState<{
    temp: number;
    humidity: number;
    windSpeed: number;
    code: number;
    locationName: string;
    apparentTemp: number;
    tempMax: number;
    tempMin: number;
    rainChance: number;
    hourly: {
      time: string;
      temp: number;
      code: number;
      rainChance: number;
    }[];
  } | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  const getWeatherConfig = (code: number) => {
    if (code === 0) {
      return { label: 'Sunny / Clear', emoji: '☀️', bg: 'bg-amber-50 border-amber-100 text-amber-900' };
    }
    if (code >= 1 && code <= 3) {
      return { label: 'Partly Cloudy', emoji: '🌤️', bg: 'bg-sky-50 border-sky-100 text-sky-900' };
    }
    if (code === 45 || code === 48) {
      return { label: 'Foggy / Hazy', emoji: '🌫️', bg: 'bg-slate-100 border-slate-200 text-slate-900' };
    }
    if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) {
      return { label: 'Rainy', emoji: '🌧️', bg: 'bg-blue-50 border-blue-100 text-blue-900' };
    }
    if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) {
      return { label: 'Snowy', emoji: '🌨️', bg: 'bg-indigo-50 border-indigo-100 text-indigo-900' };
    }
    if (code === 95 || code === 96 || code === 99) {
      return { label: 'Thunderstorm', emoji: '⛈️', bg: 'bg-purple-50 border-purple-100 text-purple-900' };
    }
    return { label: 'Cloudy', emoji: '☁️', bg: 'bg-slate-150 border-slate-200 text-slate-900' };
  };

  const getComfortConfig = (temp: number) => {
    if (temp < 10) return { label: 'Chilly', bg: 'bg-blue-50 text-blue-700 border-blue-100' };
    if (temp < 18) return { label: 'Cool', bg: 'bg-teal-50 text-teal-700 border-teal-100' };
    if (temp < 27) return { label: 'Pleasant', bg: 'bg-sky-50 text-sky-700 border-sky-100' };
    if (temp < 35) return { label: 'Warm', bg: 'bg-amber-50 text-amber-700 border-amber-100' };
    return { label: 'Hot', bg: 'bg-rose-50 text-rose-700 border-rose-100' };
  };

  const formatHourlyTime = (isoString: string, isFirst: boolean) => {
    if (isFirst) return 'Now';
    try {
      const date = new Date(isoString);
      let hours = date.getHours();
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      return `${hours} ${ampm}`;
    } catch {
      return '';
    }
  };
  const [mapRouteLoading, setMapRouteLoading] = useState(false);

  // Load hub map locations on mount
  useEffect(() => {
    if (authLoading || !user) return;
    void listHubLocations()
      .then(setHubLocations)
      .catch(() => setHubLocations([]));
  }, [authLoading, user]);

  // Load shipments & route on load/date change
  const loadCourierData = async () => {
    if (authLoading || !user) return;

    setShipmentsLoading(true);
    setRouteLoading(true);
    setRouteResult(null);
    setHighlightedOrderId(null);
    setMapMessage(null);

    // 1. Load shipments assigned to me
    try {
      const data = await listShipments({
        limit: 50,
        deliveryDay,
        courierId: 'me',
      });
      setShipments(data);
    } catch {
      setShipments([]);
    } finally {
      setShipmentsLoading(false);
    }

    // 2. Load optimized route
    try {
      const route = await predictCourierRoute('me', deliveryDay);
      setRouteResult(route);
    } catch {
      setRouteResult(null);
    } finally {
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    void loadCourierData();
  }, [authLoading, user, deliveryDay]);

  useEffect(() => {
    if (!showWeather || !highlightedOrderId || !routeResult || user?.role !== 'courier') {
      setWeatherData(null);
      return;
    }

    const chosenStop = routeResult.stops.find(s => s.order_id === highlightedOrderId);
    const isAssigned = shipments.some(s => s.order_id === highlightedOrderId);
    if (!chosenStop || !isAssigned) {
      setWeatherData(null);
      return;
    }

    const lat = chosenStop.lat_wgs84;
    const lng = chosenStop.lon_wgs84;
    if (lat == null || lng == null) {
      setWeatherData(null);
      return;
    }

    let active = true;
    const fetchWeather = async () => {
      setWeatherLoading(true);
      setWeatherError(null);
      try {
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&hourly=temperature_2m,weather_code,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&timezone=auto`
        );
        if (!response.ok) throw new Error('Weather fetch failed');
        const data = await response.json();
        
        if (active && data.current) {
          const currentHour = new Date().getHours();
          const currentRainChance = data.hourly?.precipitation_probability?.[currentHour] ?? 0;
          
          const hourlyList = [];
          if (data.hourly) {
            for (let i = 0; i < 12; i++) {
              const idx = currentHour + i;
              if (idx < data.hourly.time.length) {
                hourlyList.push({
                  time: data.hourly.time[idx],
                  temp: Math.round(data.hourly.temperature_2m[idx]),
                  code: data.hourly.weather_code[idx],
                  rainChance: data.hourly.precipitation_probability[idx]
                });
              }
            }
          }

          setWeatherData({
            temp: data.current.temperature_2m,
            humidity: data.current.relative_humidity_2m,
            windSpeed: data.current.wind_speed_10m,
            code: data.current.weather_code,
            locationName: `Shipment ${highlightedOrderId}`,
            apparentTemp: data.current.apparent_temperature,
            tempMax: data.daily?.temperature_2m_max?.[0] ? Math.round(data.daily.temperature_2m_max[0]) : Math.round(data.current.temperature_2m),
            tempMin: data.daily?.temperature_2m_min?.[0] ? Math.round(data.daily.temperature_2m_min[0]) : Math.round(data.current.temperature_2m),
            rainChance: currentRainChance,
            hourly: hourlyList
          });
        }
      } catch (err) {
        if (active) {
          setWeatherError('Failed to fetch weather.');
          setWeatherData(null);
        }
      } finally {
        if (active) setWeatherLoading(false);
      }
    };

    void fetchWeather();
    return () => { active = false; };
  }, [showWeather, highlightedOrderId, routeResult, shipments, user]);

  const mapStats = [
    {
      label: 'Assigned deliveries',
      value: shipmentsLoading ? '—' : String(shipments.length),
    },
    {
      label: 'Total duration',
      value: routeLoading ? '—' : routeResult ? `${routeResult.total_eta_minutes} min` : '—',
    },
    {
      label: 'Total stops',
      value: routeLoading ? '—' : routeResult ? String(routeResult.stops.length) : '—',
    },
  ];

  const shipmentsPanel = (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-5 py-5">
        <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
          <Truck className="h-3.5 w-3.5" />
          Active Operations
        </div>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">My shipments</h2>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Your assigned orders for the selected day.
        </p>
      </div>

      {/* Date Filter */}
      <div className="shrink-0 space-y-2 border-b border-border px-5 py-3">
        <div className="relative">
          <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="date"
            value={deliveryDay}
            onChange={(e) => setDeliveryDay(e.target.value)}
            className="rounded-lg border-border bg-white pl-10 text-sm"
          />
        </div>
      </div>

      {/* Shipment list */}
      <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {shipmentsLoading && (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        )}
        {!shipmentsLoading && shipments.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No shipments assigned for this date.
          </p>
        )}
        {!shipmentsLoading &&
          shipments.map((shipment) => (
            <div
              key={shipment.order_id}
              className={cn(
                'rounded-2xl border p-4 transition-all duration-200',
                highlightedOrderId === shipment.order_id
                  ? 'border-amber-300 bg-gradient-to-br from-amber-50/80 to-sky-50/50 shadow-md shadow-amber-100/60 ring-2 ring-amber-200/80'
                  : 'border-border bg-slate-50/80 hover:border-sky-200 hover:shadow-sm',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{shipment.order_id}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {shipment.from_hub_name} → {shipment.to_hub_name}
                  </p>
                </div>
                <span className="rounded-full bg-amber-50 px-3 py-1 text-[11px] font-semibold text-amber-700">
                  {shipment.status ?? 'In Transit'}
                </span>
              </div>

              <div className="mt-3 flex items-center justify-end gap-3 text-xs text-muted-foreground">
                <button
                  type="button"
                  onClick={() => setHighlightedOrderId(shipment.order_id)}
                  className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 transition-colors hover:bg-sky-100"
                >
                  <MapPin className="h-3 w-3" />
                  Show on map
                </button>
              </div>
            </div>
          ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1750px] flex-col px-5 sm:px-7 lg:px-10 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Courier dashboard
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">My deliveries</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            View your assigned orders, plan your route, and access the Copilot assistant.
          </p>
        </header>

        <div
          className={cn(
            'grid min-h-0 flex-1 gap-6',
            'h-[calc(100dvh-11rem)] min-h-[680px]',
            'grid-cols-1 xl:grid-cols-[minmax(340px,390px)_minmax(0,1fr)_minmax(340px,390px)]',
          )}
        >
          {/* LEFT PANEL */}
          <aside className="page-card flex min-h-0 flex-col overflow-hidden">
            {shipmentsPanel}
          </aside>

          {/* CENTER PANEL */}
          <section className="page-card flex min-h-0 flex-col overflow-hidden p-5">
            <div className="shrink-0 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                  Map-first operations
                </p>
                <h2 className="mt-1 text-2xl font-semibold">Operational map</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="status-chip bg-emerald-50 text-emerald-700">On time</span>
                <span className="status-chip bg-amber-50 text-amber-700">Delayed</span>
                <span className="status-chip bg-red-50 text-red-700">Critical</span>
              </div>
            </div>

            <div className="mt-4 grid shrink-0 grid-cols-3 gap-3 overflow-hidden rounded-xl border border-border bg-slate-50">
              {mapStats.map((stat, index) => (
                <div
                  key={stat.label}
                  className={cn('px-4 py-3.5', index < 2 && 'border-r border-border')}
                >
                  <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                    {stat.label}
                  </p>
                  <p className="mt-1.5 text-xl font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>

            <div className="relative z-0 isolate mt-4 min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-inner shadow-slate-100">
              {mapMessage && (
                <div className="absolute inset-x-3 top-3 z-[30] flex justify-center">
                  <span className="inline-flex max-w-md items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/95 px-3 py-2 text-xs font-medium text-amber-900 shadow-sm">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {mapMessage}
                  </span>
                </div>
              )}
              {mapRouteLoading && (
                <div className="absolute inset-x-0 top-3 z-[30] flex justify-center">
                  <span className="inline-flex items-center gap-2 rounded-full border border-sky-200/80 bg-white/95 px-4 py-2 text-xs font-medium text-sky-800 shadow-lg shadow-sky-100/50 backdrop-blur-sm">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
                    Plotting route…
                  </span>
                </div>
              )}
              <RouteMap
                selectedRouteId={selectedRouteId}
                onRouteSelect={setSelectedRouteId}
                activeCourierRoute={routeResult}
                highlightedOrderId={highlightedOrderId}
                onStopSelect={setHighlightedOrderId}
                showDemoRoutes={false}
                hubLocations={hubLocations}
                chinaMapOnly
              />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6 flex flex-col min-h-0">
            {/* Copilot */}
            <div className="app-panel-lg p-6 shrink-0">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Logistics Copilot</p>
                  <p className="text-xs text-muted-foreground">
                    Open the AI assistant in a dedicated view.
                  </p>
                </div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="w-full rounded-3xl bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900 border border-sky-100 hover:bg-sky-100">
                    Open Logistics Copilot
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[90vw] sm:max-w-[980px] p-0">
                  <DialogHeader className="bg-slate-950/5 px-6 py-5">
                    <DialogTitle>Logistics Copilot</DialogTitle>
                    <DialogDescription>
                      Ask about your route sequence, delays, and deliveries.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="h-[640px]">
                    <AICopilot />
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* Route Stops Sequence */}
            <div className="page-card flex min-h-0 flex-1 flex-col overflow-hidden p-0">
              <div className="shrink-0 border-b border-border px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                    Optimized Sequence
                  </p>
                  <h2 className="text-base font-semibold">Route details</h2>
                </div>
                <button
                  type="button"
                  onClick={() => setShowWeather(!showWeather)}
                  className={cn(
                    "px-2.5 py-1 rounded-full text-[10px] font-bold border transition-all duration-200 flex items-center gap-1 shrink-0",
                    showWeather 
                      ? "bg-sky-50 text-sky-700 border-sky-200" 
                      : "bg-slate-50 text-slate-500 border-slate-200"
                  )}
                >
                  {showWeather ? "⛅ Weather On" : "☁️ Weather Off"}
                </button>
              </div>

              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto custom-scrollbar p-4">
                {showWeather && !routeLoading && routeResult && (
                  <div className="pb-3 border-b border-slate-100">
                    {weatherLoading && (
                      <div className="flex items-center justify-center gap-2 py-4 text-xs text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
                        Loading weather forecast…
                      </div>
                    )}

                    {weatherError && (
                      <div className="text-xs text-red-500 py-2">
                        {weatherError}
                      </div>
                    )}

                    {!weatherLoading && !weatherError && !weatherData && (
                      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-4 text-center text-xs text-slate-500 font-semibold">
                        📍 Select a stop below to view weather forecast.
                      </div>
                    )}

                    {!weatherLoading && !weatherError && weatherData && (
                      <div className="space-y-4">
                        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                          {/* Location Row */}
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-sm">📍</span>
                            <span className="text-xs font-semibold text-slate-700 truncate">
                              {weatherData.locationName}
                            </span>
                          </div>

                          {/* Main Temp & Comfort Row */}
                          <div className="flex items-center gap-3">
                            <span className="text-2xl p-1.5 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center">
                              {getWeatherConfig(weatherData.code).emoji}
                            </span>
                            <div className="flex items-baseline">
                              <span className="text-4xl font-extrabold tracking-tight text-slate-900">
                                {Math.round(weatherData.temp)}
                              </span>
                              <span className="text-lg font-bold text-slate-500 ml-0.5">°c</span>
                            </div>
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ml-auto ${getComfortConfig(weatherData.apparentTemp).bg}`}>
                              {getComfortConfig(weatherData.apparentTemp).label}
                            </span>
                          </div>

                          {/* Condition & High/Low Row */}
                          <div className="mt-2.5 flex items-center justify-between text-xs text-slate-600">
                            <span className="font-semibold text-slate-800">
                              {getWeatherConfig(weatherData.code).label}
                            </span>
                            <span className="flex items-center gap-1.5 font-medium">
                              <span className="text-emerald-600">↑ {weatherData.tempMax}°C</span>
                              <span className="text-slate-350">|</span>
                              <span className="text-sky-600">↓ {weatherData.tempMin}°C</span>
                            </span>
                          </div>
                        </div>

                        {/* 12-Hour Scrollable Hourly Forecast */}
                        <div className="mt-4">
                          {weatherData.hourly && weatherData.hourly.length > 0 && (
                            <div className="overflow-x-auto custom-scrollbar pb-2">
                              <div style={{ width: '240%' }} className="bg-slate-50/50 rounded-xl p-3 border border-slate-200 relative">
                                <div className="flex w-full items-center justify-between relative z-10">
                                  {weatherData.hourly.map((item, idx) => (
                                    <div key={idx} className="flex flex-col items-center flex-1">
                                      <span className="text-[11px] text-slate-500 font-bold">
                                        {formatHourlyTime(item.time, idx === 0)}
                                      </span>
                                      <span className="mt-1 text-xl">
                                        {getWeatherConfig(item.code).emoji}
                                      </span>
                                      <span className="mt-0.5 text-sm font-extrabold text-slate-800">
                                        {item.temp}°
                                      </span>
                                      <span className="text-[10px] text-sky-600 font-bold mt-1 flex items-center gap-0.5">
                                        <span>☔</span>
                                        <span>{item.rainChance}%</span>
                                      </span>
                                    </div>
                                  ))}
                                </div>
                                
                                {/* SVG Sparkline Graph of Rain Probability */}
                                {(() => {
                                  const points = weatherData.hourly.map((h, i) => {
                                    const x = i * 100 + 50;
                                    const y = 28 - (h.rainChance / 100) * 24;
                                    return { x, y };
                                  });
                                  const pts = points.map((p) => `${p.x},${p.y}`).join(' ');
                                  
                                  return (
                                    <div className="relative mt-3 h-[32px]">
                                      <svg
                                        viewBox="0 0 1200 32"
                                        width="100%"
                                        height="32"
                                        preserveAspectRatio="none"
                                        className="overflow-visible"
                                      >
                                        <defs>
                                          <linearGradient id="rainSparklineGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#0284c7" stopOpacity="0.1" />
                                            <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
                                          </linearGradient>
                                        </defs>
                                        <path
                                          d={`M 50,32 ` + points.map(p => `L ${p.x},${p.y}`).join(' ') + ` L 1150,32 Z`}
                                          fill="url(#rainSparklineGrad)"
                                        />
                                        <polyline
                                          fill="none"
                                          stroke="#0284c7"
                                          strokeWidth="2"
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          points={pts}
                                        />
                                        {points.map((p, idx) => (
                                          <circle
                                            key={idx}
                                            cx={p.x}
                                            cy={p.y}
                                            r="3.5"
                                            fill="#0284c7"
                                            stroke="#ffffff"
                                            strokeWidth="2"
                                          />
                                        ))}
                                      </svg>
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {routeLoading && (
                  <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
                    Loading route stops…
                  </div>
                )}
                {!routeLoading && !routeResult && (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No active route sequence found.
                  </p>
                )}
                {!routeLoading &&
                  routeResult &&
                  routeResult.stops.map((stop) => (
                    <div
                      key={stop.order_id}
                      onClick={() => setHighlightedOrderId(stop.order_id)}
                      className={cn(
                        'rounded-xl border p-3 text-sm transition cursor-pointer',
                        highlightedOrderId === stop.order_id
                          ? 'border-amber-300 bg-amber-50/50 shadow-sm ring-1 ring-amber-200'
                          : 'border-border bg-slate-50/60 hover:border-sky-200',
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-xs text-muted-foreground">
                          Stop #{stop.sequence}
                        </span>
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                          {stop.eta_minutes} min
                        </span>
                      </div>
                      <p className="mt-1.5 font-semibold text-xs font-mono">{stop.order_id}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {stop.from_hub_name} → {stop.to_hub_name}
                      </p>
                      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>From start: +{stop.eta_from_start_minutes}m</span>
                        <span className="font-medium text-slate-800">Arrival: {stop.estimated_arrival}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}