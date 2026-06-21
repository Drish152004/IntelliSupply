import { useEffect, useState } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import AICopilot from '@/components/AICopilot';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { CitySelect, HubSelect } from '@/components/logistics/LocationSelect';
import { useLogisticsLocations } from '@/hooks/useLogisticsLocations';
import {
  createShipment,
  getShipment,
  getLogisticsKpis,
  listShipments,
  listDeliveryDays,
  listCouriersWithOrders,
  listHubLocations,
  predictCourierRoute,
  type CourierListItem,
  type CourierRouteResult,
  type HubMapLocation,
  type LogisticsKpis,
  type OrderDetail,
  type ShipmentListItem,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Plus,
  Sparkles,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Truck,
  ShieldCheck,
  Route,
  ChevronDown,
  MapPin,
  List,
  Search,
  Sun,
  CloudSun,
  Cloud,
  CloudRain,
  CloudSnow,
  CloudLightning,
  Wind,
  Droplets,
  Thermometer,
} from 'lucide-react';

const dispatchChecklist = [
  'Verify cargo documentation',
  'Confirm hub slot availability',
  'Assign driver and vehicle',
];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatRouteStartTime(routeStartTime?: string | null): string {
  if (!routeStartTime) return '—';
  if (routeStartTime.length >= 16) return routeStartTime.slice(11, 16);
  if (routeStartTime.length >= 5) return routeStartTime.slice(0, 5);
  return routeStartTime;
}

export default function LogisticsDashboard() {
  const { user, loading: authLoading } = useAuth();
  const isManager = user?.role === 'admin' || user?.role === 'logistics_manager';
  const isCourier = user?.role === 'courier';

  const [selectedRouteId, setSelectedRouteId] = useSessionStorageState<string | null>('logistics_route_id', null);
  const [highlightedOrderId, setHighlightedOrderId] = useSessionStorageState<string | null>('logistics_highlighted_order_id', null);
  const [mapRouteLoading, setMapRouteLoading] = useState(false);

  // ── Add-shipment form (managers only) ────────────────────────────────────
  const [showShipmentForm, setShowShipmentForm] = useState(true);
  const [shipmentCityName, setShipmentCityName] = useState('');
  const [fromHubName, setFromHubName] = useState('');
  const [toHubName, setToHubName] = useState('');
  const { cities: shipmentCities, hubs: shipmentHubs, loadingHubs: shipmentHubsLoading } =
    useLogisticsLocations(shipmentCityName);
  const [deliveryDate, setDeliveryDate] = useState('');
  const [receiptTime, setReceiptTime] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{
    orderId: string;
    courierId?: string;
    courierName?: string;
    courierHub?: string;
  } | null>(null);

  // ── Current shipments panel ────────────────────────────────────────────
  const [currentShipments, setCurrentShipments] = useState<ShipmentListItem[]>([]);
  const [shipmentsLoading, setShipmentsLoading] = useState(false);
  const [filterDeliveryDay, setFilterDeliveryDay] = useSessionStorageState('logistics_delivery_day', todayISO());
  const [deliveryDaysLoaded, setDeliveryDaysLoaded] = useState(false);
  const [mapMessage, setMapMessage] = useState<string | null>(null);

  // Manager courier dropdown
  const [couriers, setCouriers] = useState<CourierListItem[]>([]);
  const [selectedCourierId, setSelectedCourierId] = useSessionStorageState<string>('logistics_courier_id', '');

  // ── Order detail dialog ────────────────────────────────────────────────
  const [detailOpen, setDetailOpen] = useState(false);
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // ── Route dialog ───────────────────────────────────────────────────────
  const [routeOpen, setRouteOpen] = useState(false);
  const [routeResult, setRouteResult] = useState<CourierRouteResult | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  // ── Hub map + all shipments ────────────────────────────────────────────
  const [hubLocations, setHubLocations] = useState<HubMapLocation[]>([]);
  const [allShipmentsOpen, setAllShipmentsOpen] = useState(false);
  const [allShipments, setAllShipments] = useState<ShipmentListItem[]>([]);
  const [allShipmentsLoading, setAllShipmentsLoading] = useState(false);
  const [allShipmentsSearch, setAllShipmentsSearch] = useState('');
  const [showAllDates, setShowAllDates] = useSessionStorageState('logistics_show_all_dates', false);
  const [logisticsKpis, setLogisticsKpis] = useState<LogisticsKpis | null>(null);
  const [kpisLoading, setKpisLoading] = useState(false);

  // ── Weather Intelligence ───────────────────────────────────────────────
  const [weatherTab, setWeatherTab] = useState<'hourly' | 'daily'>('hourly');
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
    daily: {
      date: string;
      tempMax: number;
      tempMin: number;
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

  const formatDailyDate = (isoString: string, isFirst: boolean) => {
    if (isFirst) return 'Today';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', { weekday: 'short' });
    } catch {
      return '';
    }
  };

  useEffect(() => {
    let active = true;
    
    const fetchWeatherForLocation = async (lat: number, lng: number, name: string) => {
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
            for (let i = 0; i < 6; i++) {
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

          const dailyList = [];
          if (data.daily) {
            for (let i = 0; i < 5; i++) {
              if (i < data.daily.time.length) {
                dailyList.push({
                  date: data.daily.time[i],
                  tempMax: Math.round(data.daily.temperature_2m_max[i]),
                  tempMin: Math.round(data.daily.temperature_2m_min[i]),
                  code: data.daily.weather_code[i],
                  rainChance: data.daily.precipitation_probability_max[i]
                });
              }
            }
          }

          setWeatherData({
            temp: data.current.temperature_2m,
            humidity: data.current.relative_humidity_2m,
            windSpeed: data.current.wind_speed_10m,
            code: data.current.weather_code,
            locationName: name,
            apparentTemp: data.current.apparent_temperature,
            tempMax: data.daily?.temperature_2m_max?.[0] ? Math.round(data.daily.temperature_2m_max[0]) : Math.round(data.current.temperature_2m),
            tempMin: data.daily?.temperature_2m_min?.[0] ? Math.round(data.daily.temperature_2m_min[0]) : Math.round(data.current.temperature_2m),
            rainChance: currentRainChance,
            hourly: hourlyList,
            daily: dailyList
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

    // 1. Check if there is an active courier route
    if (routeResult) {
      let lat: number | undefined;
      let lng: number | undefined;
      let name = routeResult.courier_name 
        ? `Courier ${routeResult.courier_name} Route` 
        : `Courier Route (${routeResult.courier_id})`;

      if (routeResult.courier_start) {
        lat = routeResult.courier_start.lat;
        lng = routeResult.courier_start.lng;
      } else if (routeResult.stops?.length) {
        const firstStop = routeResult.stops[0];
        lat = firstStop.from_lat ?? firstStop.lat_wgs84;
        lng = firstStop.from_lng ?? firstStop.lon_wgs84;
      }

      if (lat != null && lng != null) {
        void fetchWeatherForLocation(lat, lng, name);
        return () => { active = false; };
      }
    }

    // 2. Fallback: Check if there are hub locations
    if (hubLocations && hubLocations.length > 0) {
      const firstHub = hubLocations[0];
      void fetchWeatherForLocation(firstHub.lat, firstHub.lng, `Hub Area: ${firstHub.hub_name}`);
      return () => { active = false; };
    }

    setWeatherData(null);
    return () => { active = false; };
  }, [routeResult, hubLocations]);

  useEffect(() => {
    setRouteResult(null);
    setHighlightedOrderId(null);
  }, [selectedCourierId, filterDeliveryDay, showAllDates]);

  useEffect(() => {
    if (authLoading || !user) return;
    void listHubLocations()
      .then(setHubLocations)
      .catch(() => setHubLocations([]));
  }, [authLoading, user]);

  // Pick a delivery day that actually has shipments (today if available, else latest).
  useEffect(() => {
    if (authLoading || !user) return;
    void listDeliveryDays()
      .then((days) => {
        if (!days.length) return;
        const today = todayISO();
        setFilterDeliveryDay((prev) => {
          if (prev && days.includes(prev)) return prev;
          if (days.includes(today)) return today;
          return days[0];
        });
      })
      .catch(() => {
        // Keep today as fallback.
      })
      .finally(() => setDeliveryDaysLoaded(true));
  }, [authLoading, user]);

  // ── Load couriers with orders for the selected delivery day ───────────
  useEffect(() => {
    if (!isManager || !deliveryDaysLoaded || showAllDates) return;
    const day = filterDeliveryDay || todayISO();
    void listCouriersWithOrders(day)
      .then((rows) => {
        setCouriers(rows);
        setSelectedCourierId((prev) =>
          prev && rows.some((c) => c.courier_id === prev) ? prev : '',
        );
      })
      .catch(() => {
        setCouriers([]);
        setSelectedCourierId('');
      });
  }, [isManager, filterDeliveryDay, deliveryDaysLoaded, showAllDates]);

  const loadAllShipments = () => {
    setAllShipmentsLoading(true);
    void listShipments({ limit: 200 })
      .then(setAllShipments)
      .catch(() => setAllShipments([]))
      .finally(() => setAllShipmentsLoading(false));
  };

  const openAllShipmentsDialog = () => {
    setAllShipmentsOpen(true);
    setAllShipmentsSearch('');
    loadAllShipments();
  };

  const filteredAllShipments = allShipments.filter((shipment) => {
    if (!allShipmentsSearch.trim()) return true;
    const q = allShipmentsSearch.trim().toLowerCase();
    return (
      shipment.order_id.toLowerCase().includes(q) ||
      (shipment.from_hub_name ?? '').toLowerCase().includes(q) ||
      (shipment.to_hub_name ?? '').toLowerCase().includes(q) ||
      (shipment.city_name ?? '').toLowerCase().includes(q) ||
      (shipment.assigned_courier_name ?? '').toLowerCase().includes(q) ||
      (shipment.delivery_day ?? '').includes(q)
    );
  });

  // ── Load shipments (role-aware) ───────────────────────────────────────
  const loadShipments = () => {
    if (authLoading || !user || !deliveryDaysLoaded) return;
    setShipmentsLoading(true);
    void listShipments({
      limit: showAllDates ? 200 : 50,
      courierId: isManager && selectedCourierId ? selectedCourierId : undefined,
      deliveryDay: showAllDates ? undefined : filterDeliveryDay || undefined,
    })
      .then(setCurrentShipments)
      .catch(() => setCurrentShipments([]))
      .finally(() => setShipmentsLoading(false));
  };

  useEffect(() => {
    loadShipments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, filterDeliveryDay, selectedCourierId, deliveryDaysLoaded, showAllDates]);

  useEffect(() => {
    if (authLoading || !user || !deliveryDaysLoaded) return;
    const day = showAllDates ? undefined : filterDeliveryDay || undefined;
    setKpisLoading(true);
    void getLogisticsKpis(day)
      .then(setLogisticsKpis)
      .catch(() => setLogisticsKpis(null))
      .finally(() => setKpisLoading(false));
  }, [authLoading, user, filterDeliveryDay, deliveryDaysLoaded, showAllDates]);

  const mapStats = [
    {
      label: 'Active shipments',
      value: kpisLoading ? '—' : String(logisticsKpis?.active_shipments ?? 0),
    },
    {
      label: 'At-risk shipments',
      value: kpisLoading ? '—' : String(logisticsKpis?.at_risk_shipments ?? 0),
    },
    {
      label: 'Unassigned',
      value: kpisLoading ? '—' : String(logisticsKpis?.unassigned_shipments ?? 0),
    },
  ];

  const routeOpsStats = [
    {
      label: 'Active shipments',
      value: kpisLoading ? '—' : String(logisticsKpis?.active_shipments ?? 0),
    },
    {
      label: 'Courier assignment',
      value: kpisLoading ? '—' : `${logisticsKpis?.courier_assignment_pct ?? 0}%`,
    },
    {
      label: 'At-risk shipments',
      value: kpisLoading ? '—' : String(logisticsKpis?.at_risk_shipments ?? 0),
    },
    {
      label: 'Hub coverage',
      value: kpisLoading ? '—' : String(logisticsKpis?.hub_coverage ?? 0),
    },
  ];

  const kpiCallouts = logisticsKpis?.callouts ?? [];

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  // ── View order detail ─────────────────────────────────────────────────
  const handleViewDetails = async (orderId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setOrderDetail(null);
    try {
      const order = await getShipment(orderId);
      setOrderDetail(order);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load order details.');
    } finally {
      setDetailLoading(false);
    }
  };

  // ── Create shipment ────────────────────────────────────────────────────
  const handleShipmentCityChange = (city: string) => {
    setShipmentCityName(city);
    setFromHubName('');
    setToHubName('');
  };

  const handleFromHubChange = (hub: string) => {
    setFromHubName(hub);
    if (toHubName === hub) {
      setToHubName('');
    }
  };

  const handleCreateShipment = async () => {
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    if (!shipmentCityName || !fromHubName || !toHubName) {
      setError('Please select a city, source hub, and destination hub.');
      setSubmitting(false);
      return;
    }
    if (fromHubName === toHubName) {
      setError('Source and destination hubs must be different.');
      setSubmitting(false);
      return;
    }
    try {
      let receiptTimeFormatted: string | undefined;
      if (receiptTime) {
        receiptTimeFormatted = receiptTime.length === 5 ? `${receiptTime}:00` : receiptTime;
      }
      const result = await createShipment({
        from_hub_name: fromHubName.trim(),
        to_hub_name: toHubName.trim(),
        delivery_date: deliveryDate,
        receipt_time: receiptTimeFormatted,
        notes: notes.trim() || undefined,
      });
      setSuccess({
        orderId: result.order?.order_id ?? '',
        courierId: result.order?.assigned_courier_id,
        courierName: result.order?.assigned_courier_name,
        courierHub: result.order?.assigned_courier_hub_name,
      });
      loadShipments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create shipment.');
    } finally {
      setSubmitting(false);
    }
  };

  const loadCourierRoute = async (
    courierId: 'me' | string,
    options: {
      openDialog?: boolean;
      highlightOrderId?: string | null;
      deliveryDay?: string;
    } = {},
  ) => {
    const {
      openDialog = true,
      highlightOrderId = null,
      deliveryDay = filterDeliveryDay || todayISO(),
    } = options;
    if (openDialog) {
      setRouteOpen(true);
      setRouteLoading(true);
      setRouteError(null);
      setRouteResult(null);
    } else {
      setMapRouteLoading(true);
    }

    try {
      const result = await predictCourierRoute(courierId, deliveryDay);
      setRouteResult(result);
      setHighlightedOrderId(highlightOrderId);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Route prediction failed.';
      if (openDialog) {
        setRouteError(message);
      }
      throw err;
    } finally {
      if (openDialog) {
        setRouteLoading(false);
      } else {
        setMapRouteLoading(false);
      }
    }
  };

  // ── Predict route ──────────────────────────────────────────────────────
  const handlePredictRoute = async (courierId: 'me' | string) => {
    await loadCourierRoute(courierId, { openDialog: true });
  };

  const handleShowShipmentOnMap = async (shipment: ShipmentListItem) => {
    setMapMessage(null);
    const courierId = isCourier ? 'me' : shipment.assigned_courier_id;
    if (!courierId) {
      setMapMessage('This shipment has no assigned courier yet — assign a courier to show it on the map.');
      return;
    }

    const activeCourierId =
      courierId === 'me' ? user?.courier_id ?? 'me' : courierId;

    if (!routeResult || routeResult.courier_id !== activeCourierId) {
      try {
        await loadCourierRoute(courierId, {
          openDialog: false,
          highlightOrderId: shipment.order_id,
          deliveryDay: shipment.delivery_day || filterDeliveryDay || todayISO(),
        });
      } catch (err) {
        setMapMessage(
          err instanceof Error ? err.message : 'Could not load courier route for this shipment.',
        );
        setHighlightedOrderId(shipment.order_id);
      }
    } else {
      setHighlightedOrderId(shipment.order_id);
    }
  };

  // ── Current shipments panel content ───────────────────────────────────
  const shipmentsPanel = (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-5 py-5">
        <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">
          <Truck className="h-3.5 w-3.5" />
          Active operations
        </div>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">
          {isCourier ? 'My shipments' : 'Current shipments'}
        </h2>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {isCourier
            ? 'Your assigned orders for the selected day.'
            : 'Live dispatches across operational hubs.'}
        </p>
      </div>

      {/* Filters */}
      <div className="shrink-0 space-y-2 border-b border-border px-5 py-3">
        {/* Manager: courier selector */}
        {isManager && (
          <div className="relative">
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <select
              value={selectedCourierId}
              onChange={(e) => setSelectedCourierId(e.target.value)}
              className="w-full appearance-none rounded-lg border border-border bg-slate-50 py-2 pl-3 pr-8 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-slate-400"
            >
              <option value="">All couriers with orders</option>
              {couriers.map((c) => (
                <option key={c.courier_id} value={c.courier_id}>
                  {c.name || c.email}
                  {c.email && c.name ? ` (${c.email})` : ''}
                  {c.order_count != null ? ` — ${c.order_count} order${c.order_count === 1 ? '' : 's'}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Delivery day picker */}
        <div className="space-y-2">
          <div className="relative">
            <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="date"
              value={filterDeliveryDay}
              onChange={(e) => {
                setShowAllDates(false);
                setFilterDeliveryDay(e.target.value);
              }}
              disabled={showAllDates}
              className="rounded-lg border-border bg-white pl-10 text-sm disabled:opacity-50"
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-slate-50 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={showAllDates}
              onChange={(e) => setShowAllDates(e.target.checked)}
              className="h-4 w-4 rounded border-border text-sky-600 focus:ring-sky-500"
            />
            <span className="text-foreground">Show all dates in list</span>
          </label>

          <Button
            type="button"
            variant="outline"
            onClick={openAllShipmentsDialog}
            className="w-full justify-start gap-2 rounded-lg border-border bg-white text-sm font-medium"
          >
            <List className="h-4 w-4 shrink-0" />
            View all orders (history)
          </Button>
        </div>
      </div>

      {/* Shipment cards */}
      <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {shipmentsLoading && (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        )}
        {!shipmentsLoading && currentShipments.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {showAllDates
              ? 'No shipments found for the selected filters.'
              : 'No shipments found for this date. Try another date or open all orders.'}
          </p>
        )}
        {!shipmentsLoading &&
          currentShipments.map((shipment) => (
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

              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>
                  Courier:{' '}
                  {shipment.assigned_courier_name ?? shipment.assigned_courier_id ?? 'Unassigned'}
                </span>
                {showAllDates && shipment.delivery_day && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium">
                    {shipment.delivery_day}
                  </span>
                )}
              </div>

              <div className="mt-3 flex items-center justify-end gap-3 text-xs text-muted-foreground">
                <button
                  type="button"
                  onClick={() => void handleShowShipmentOnMap(shipment)}
                  className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 transition-colors hover:bg-sky-100"
                >
                  <MapPin className="h-3 w-3" />
                  Show on map
                </button>
                {isManager && (
                  <button
                    type="button"
                    onClick={() => void handleViewDetails(shipment.order_id)}
                    className="font-medium text-slate-900 hover:underline"
                  >
                    View details
                  </button>
                )}
              </div>
            </div>
          ))}
      </div>

      {/* Bottom action */}
      <div className="shrink-0 border-t border-border px-5 py-4 space-y-2">
        {isCourier && (
          <Button
            type="button"
            onClick={() => void handlePredictRoute('me')}
            className="flex w-full items-center rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white hover:bg-sky-700"
          >
            <Route className="mr-2 h-4 w-4 shrink-0" />
            My route
            <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
          </Button>
        )}
        {isManager && selectedCourierId && (
          <Button
            type="button"
            onClick={() => void handlePredictRoute(selectedCourierId)}
            className="flex w-full items-center rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white hover:bg-sky-700"
          >
            <Route className="mr-2 h-4 w-4 shrink-0" />
            View route &amp; ETA
            <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="mx-auto flex max-w-[1750px] flex-col px-5 sm:px-7 lg:px-10 pb-8">
        <header className="shrink-0 pt-6 pb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">
            Operations
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {isCourier ? 'My deliveries' : 'Logistics command center'}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {isCourier
              ? 'View your assigned orders and plan your delivery route.'
              : 'Create shipments, monitor routes on the live map, and resolve delays with AI-assisted dispatch.'}
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
            {isCourier ? (
              // Couriers see shipments only — no add shipment toggle
              shipmentsPanel
            ) : (
              <>
                {/* Manager toggle */}
                <div className="border-b border-border px-5 pt-5 pb-4">
                  <div className="flex items-center justify-between rounded-2xl border border-border bg-slate-50 p-1">
                    <button
                      onClick={() => setShowShipmentForm(true)}
                      className={cn(
                        'flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold transition',
                        showShipmentForm
                          ? 'bg-black text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-100',
                      )}
                    >
                      Add shipment
                    </button>
                    <button
                      onClick={() => setShowShipmentForm(false)}
                      className={cn(
                        'flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold transition',
                        !showShipmentForm
                          ? 'bg-black text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-100',
                      )}
                    >
                      Current shipments
                    </button>
                  </div>
                </div>

                {showShipmentForm ? (
                  <>
                    {/* Add shipment form */}
                    <div className="shrink-0 border-b border-border px-5 pb-4 pt-5">
                      <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-600">
                        <Sparkles className="h-3.5 w-3.5 text-slate-700" />
                        New dispatch
                      </div>
                      <h2 className="mt-3 text-xl font-semibold tracking-tight">Add shipment</h2>
                      <p className="mt-1.5 text-sm text-muted-foreground">
                        Hub-to-hub dispatch with auto courier assignment.
                      </p>
                    </div>

                    <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
                      <div className="space-y-3">
                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <CitySelect
                            label="City"
                            value={shipmentCityName}
                            onChange={handleShipmentCityChange}
                            cities={shipmentCities}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <HubSelect
                            label="From hub"
                            value={fromHubName}
                            onChange={handleFromHubChange}
                            hubs={shipmentHubs}
                            disabled={!shipmentCityName || shipmentHubsLoading}
                            placeholder={shipmentCityName ? 'Select source hub' : 'Select city first'}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <HubSelect
                            label="To hub"
                            value={toHubName}
                            onChange={setToHubName}
                            hubs={shipmentHubs.filter((h) => h.hub_name !== fromHubName)}
                            disabled={!shipmentCityName || shipmentHubsLoading || !fromHubName}
                            placeholder={fromHubName ? 'Select destination hub' : 'Select source hub first'}
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Delivery date
                          </Label>
                          <div className="relative mt-2">
                            <Calendar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                              type="date"
                              value={deliveryDate}
                              onChange={(e) => setDeliveryDate(e.target.value)}
                              className="rounded-lg border-border bg-white pl-10 text-sm"
                            />
                          </div>
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Receipt time
                          </Label>
                          <Input
                            type="time"
                            step={1}
                            value={receiptTime}
                            onChange={(e) => setReceiptTime(e.target.value)}
                            className="mt-2 rounded-lg border-border bg-white text-sm"
                          />
                        </div>

                        <div className="rounded-xl border border-border bg-slate-50/80 p-3.5">
                          <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                            Notes
                          </Label>
                          <Textarea
                            placeholder="Optional notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="mt-2 min-h-[72px] rounded-lg border-border bg-white text-sm"
                          />
                        </div>

                        {error && (
                          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                            {error}
                          </div>
                        )}

                        {success && (
                          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                            <p className="font-semibold">Shipment created</p>
                            <p className="mt-1 text-xs">Order: {success.orderId}</p>
                            {success.courierName && (
                              <p className="text-xs">
                                Courier: {success.courierName}
                                {success.courierId ? ` (${success.courierId})` : ''}
                              </p>
                            )}
                            {success.courierHub && (
                              <p className="text-xs">Hub: {success.courierHub}</p>
                            )}
                          </div>
                        )}

                        <Button
                          type="button"
                          disabled={submitting}
                          onClick={handleCreateShipment}
                          className="flex w-full items-center rounded-xl bg-slate-950 px-4 py-3.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
                        >
                          {submitting ? (
                            <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" />
                          ) : (
                            <Plus className="mr-2 h-4 w-4 shrink-0" />
                          )}
                          Create shipment
                          <ArrowRight className="ml-auto h-4 w-4 shrink-0" />
                        </Button>

                        <p className="text-center text-xs text-muted-foreground">
                          Auto-assigns courier based on proximity and hub availability.
                        </p>
                      </div>
                    </div>

                    {/* Dispatch checklist */}
                    <div className="shrink-0 border-t border-border bg-slate-50/60 px-5 py-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                        Dispatch checklist
                      </p>
                      <ul className="mt-3 space-y-2">
                        {dispatchChecklist.map((item) => (
                          <li key={item} className="flex items-start gap-2 text-xs text-muted-foreground">
                            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </>
                ) : (
                  // Manager viewing current shipments
                  shipmentsPanel
                )}
              </>
            )}
          </aside>

          {/* CENTER */}
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
                    Plotting courier route…
                  </span>
                </div>
              )}
              <RouteMap
                selectedRouteId={selectedRouteId}
                onRouteSelect={handleRouteSelect}
                activeCourierRoute={routeResult}
                highlightedOrderId={highlightedOrderId}
                onStopSelect={setHighlightedOrderId}
                showDemoRoutes={!routeResult}
                hubLocations={hubLocations}
                chinaMapOnly
              />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6">
            {/* Copilot (managers only) */}
            {isManager && (
              <div className="app-panel-lg p-6">
                <div className="flex items-center gap-3 mb-4">
                  <ShieldCheck className="h-5 w-5 text-sky-600" />
                  <div>
                    <p className="text-sm font-semibold text-foreground">Logistics Copilot</p>
                    <p className="text-xs text-muted-foreground">
                      Open the AI dispatch assistant in a dedicated view.
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
                        Ask about route planning, delays, courier assignment, and shipment
                        prioritization.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="h-[640px]">
                      <AICopilot />
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            )}

            {/* Route operations */}
            <div className="page-card flex min-h-0 flex-col overflow-hidden p-0">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Live logistics
                </p>
                <h2 className="text-base font-semibold">Route operations</h2>
              </div>

              <div className="grid shrink-0 grid-cols-2 gap-2 border-b border-border p-3">
                {routeOpsStats.map((stat) => (
                  <div key={stat.label} className="rounded-lg border border-border bg-slate-50/80 p-3">
                    <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-1 text-lg font-semibold">{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto custom-scrollbar p-3">
                {kpisLoading && (
                  <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading KPIs…
                  </div>
                )}
                {!kpisLoading &&
                  kpiCallouts.map((callout) => (
                    <div
                      key={callout.title}
                      className={cn(
                        'rounded-lg p-3 text-sm',
                        callout.severity === 'critical'
                          ? 'border border-red-100 bg-red-50/80 text-red-950'
                          : callout.severity === 'warning'
                            ? 'border border-amber-100 bg-amber-50/80 text-amber-950'
                            : 'bg-slate-50',
                      )}
                    >
                      <p className="font-semibold">{callout.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{callout.detail}</p>
                    </div>
                  ))}
              </div>
            </div>

            {/* Weather intelligence */}
            <div className="page-card flex shrink-0 flex-col overflow-hidden p-0 bg-white border border-border shadow-sm rounded-xl">
              <div className="shrink-0 border-b border-border px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Regional conditions
                </p>
                <h2 className="text-base font-semibold text-slate-900">Weather intelligence</h2>
              </div>

              <div className="p-4 space-y-4">
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

                {!weatherLoading && !weatherError && weatherData && (
                  <>
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

                      {/* Details Rows (Feels Like & Rain Chance) */}
                      <div className="mt-4 pt-3 border-t border-slate-200/60 space-y-2">
                        <div className="flex items-center justify-between text-xs bg-white p-2.5 rounded-lg border border-slate-200 shadow-sm">
                          <span className="flex items-center gap-2 text-slate-600 font-medium">
                            <span className="text-sm">🌡️</span>
                            Feels Like
                          </span>
                          <span className="font-bold text-slate-900">
                            {Math.round(weatherData.apparentTemp)}°C
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs bg-white p-2.5 rounded-lg border border-slate-200 shadow-sm">
                          <span className="flex items-center gap-2 text-slate-600 font-medium">
                            <span className="text-sm">☔</span>
                            Chances of Rain
                          </span>
                          <span className="font-bold text-slate-900">
                            {weatherData.rainChance}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Forecast Switcher Tab Row */}
                    <div className="mt-6">
                      <div className="bg-slate-100 p-0.5 rounded-lg flex gap-1 mb-4 text-[10px] font-bold w-fit border border-slate-200">
                        <button
                          type="button"
                          onClick={() => setWeatherTab('hourly')}
                          className={cn(
                            "rounded px-3 py-1.5 transition-all",
                            weatherTab === 'hourly'
                              ? "bg-white text-slate-900 shadow-sm border border-slate-200/50 font-bold"
                              : "text-slate-500 hover:text-slate-800"
                          )}
                        >
                          Hourly
                        </button>
                        <button
                          type="button"
                          onClick={() => setWeatherTab('daily')}
                          className={cn(
                            "rounded px-3 py-1.5 transition-all",
                            weatherTab === 'daily'
                              ? "bg-white text-slate-900 shadow-sm border border-slate-200/50 font-bold"
                              : "text-slate-500 hover:text-slate-800"
                          )}
                        >
                          Daily
                        </button>
                      </div>

                      {/* Hourly forecast panel */}
                      {weatherTab === 'hourly' && weatherData.hourly && weatherData.hourly.length > 0 && (
                        <div className="bg-slate-50/50 rounded-xl p-3 border border-slate-200">
                          <div className="flex w-full items-center justify-between">
                            {weatherData.hourly.map((item, idx) => (
                              <div key={idx} className="flex flex-col items-center flex-1">
                                <span className="text-[9px] text-slate-500 font-semibold">
                                  {formatHourlyTime(item.time, idx === 0)}
                                </span>
                                <span className="mt-1.5 text-lg p-0.5">
                                  {getWeatherConfig(item.code).emoji}
                                </span>
                                <span className="mt-1 text-xs font-bold text-slate-800">
                                  {item.temp}°
                                </span>
                              </div>
                            ))}
                          </div>
                          
                          {/* SVG Sparkline Graph */}
                          {(() => {
                            const temps = weatherData.hourly.map((h) => h.temp);
                            const maxT = Math.max(...temps);
                            const minT = Math.min(...temps);
                            const points = weatherData.hourly.map((h, i) => {
                              const x = i * 100 + 50;
                              const y = maxT === minT ? 16 : 26 - ((h.temp - minT) / (maxT - minT)) * 20;
                              return { x, y };
                            });
                            const pts = points.map((p) => `${p.x},${p.y}`).join(' ');
                            
                            return (
                              <div className="relative mt-2">
                                <svg
                                  viewBox="0 0 600 32"
                                  width="100%"
                                  height="32"
                                  preserveAspectRatio="none"
                                  className="overflow-visible"
                                >
                                  <defs>
                                    <linearGradient id="sparklineGrad" x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="0%" stopColor="#0284c7" stopOpacity="0.08" />
                                      <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
                                    </linearGradient>
                                  </defs>
                                  <path
                                    d={`M 50,32 L 50,${points[0].y} L 150,${points[1].y} L 250,${points[2].y} L 350,${points[3].y} L 450,${points[4].y} L 550,${points[5].y} L 550,32 Z`}
                                    fill="url(#sparklineGrad)"
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
                      )}

                      {/* Daily forecast panel */}
                      {weatherTab === 'daily' && weatherData.daily && weatherData.daily.length > 0 && (
                        <div className="bg-slate-50/50 rounded-xl p-3 border border-slate-200 divide-y divide-slate-200/80">
                          {weatherData.daily.map((item, idx) => (
                            <div key={idx} className="flex items-center justify-between text-xs py-2.5 first:pt-0 last:pb-0">
                              <span className="w-16 font-semibold text-slate-600">
                                {formatDailyDate(item.date, idx === 0)}
                              </span>
                              <span className="flex items-center gap-2">
                                <span className="text-base">
                                  {getWeatherConfig(item.code).emoji}
                                </span>
                                {item.rainChance > 10 && (
                                  <span className="text-[9px] font-bold text-sky-600 bg-sky-50 px-1 py-0.5 rounded border border-sky-100">
                                    ☔ {item.rainChance}%
                                  </span>
                                )}
                              </span>
                              <span className="font-bold text-slate-800">
                                {item.tempMin}° / {item.tempMax}°
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Weather Icon Mapping Legend */}
                    <div className="border-t border-border pt-4 mt-5">
                      <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-400 mb-2.5">
                        Condition key
                      </p>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-[10px] text-slate-500">
                        <div className="flex items-center gap-1.5">
                          <span>☀️</span>
                          <span>0: Clear / Sunny</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>🌤️</span>
                          <span>1-3: Cloudy</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>🌫️</span>
                          <span>45-48: Foggy</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>🌧️</span>
                          <span>51-82: Rainy</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>🌨️</span>
                          <span>71-86: Snowy</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>⛈️</span>
                          <span>95-99: Storm</span>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* ── Order detail dialog (managers only) ─────────────────────────── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Shipment details</DialogTitle>
            <DialogDescription>Order and assigned courier information.</DialogDescription>
          </DialogHeader>

          {detailLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading order details…
            </div>
          )}

          {detailError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {detailError}
            </div>
          )}

          {orderDetail && !detailLoading && (
            <div className="space-y-4 text-sm">
              <div className="rounded-xl border border-border bg-slate-50 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Order
                </p>
                <p className="mt-2 font-semibold">{orderDetail.order_id}</p>
                <p className="mt-1 text-muted-foreground">
                  {orderDetail.from_hub_name ?? '—'} → {orderDetail.to_hub_name ?? '—'}
                </p>
                {orderDetail.city_name && (
                  <p className="mt-1 text-muted-foreground">City: {orderDetail.city_name}</p>
                )}
                {orderDetail.delivery_day && (
                  <p className="mt-1 text-muted-foreground">Delivery: {orderDetail.delivery_day}</p>
                )}
                {orderDetail.receipt_time && (
                  <p className="mt-1 text-muted-foreground">Receipt: {orderDetail.receipt_time}</p>
                )}
                {orderDetail.notes && (
                  <p className="mt-2 text-muted-foreground">Notes: {orderDetail.notes}</p>
                )}
              </div>

              <div className="rounded-xl border border-border bg-slate-50 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Assigned courier
                </p>
                {orderDetail.assigned_courier_id ? (
                  <>
                    <p className="mt-2 font-semibold">
                      {orderDetail.assigned_courier_name ?? orderDetail.assigned_courier_id}
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      ID: {orderDetail.assigned_courier_id}
                    </p>
                    {orderDetail.assigned_courier_hub_name && (
                      <p className="mt-1 text-muted-foreground">
                        Hub: {orderDetail.assigned_courier_hub_name}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-2 text-muted-foreground">No courier assigned.</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ── Route dialog ─────────────────────────────────────────────────── */}
      <Dialog open={routeOpen} onOpenChange={setRouteOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {routeResult
                ? `Route for ${routeResult.courier_name ?? routeResult.courier_id}`
                : 'Delivery route'}
            </DialogTitle>
            <DialogDescription>
              {routeResult ? (
                <>
                  {routeResult.delivery_day} · Starting {formatRouteStartTime(routeResult.route_start_time)} ·{' '}
                  {routeResult.total_eta_minutes} min total
                  {routeResult.source === 'graphdb' && (
                    <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      Saved route
                    </span>
                  )}
                  {routeResult.source === 'ml_model' && (
                    <span className="ml-2 rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-800">
                      Predicted now
                    </span>
                  )}
                </>
              ) : (
                'Delivery sequence with ETA for each stop.'
              )}
            </DialogDescription>
          </DialogHeader>

          {routeLoading && (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading route…
            </div>
          )}

          {routeError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {routeError}
            </div>
          )}

          {routeResult && !routeLoading && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    <th className="pb-2 pr-4">#</th>
                    <th className="pb-2 pr-4">Order</th>
                    <th className="pb-2 pr-4">Route</th>
                    <th className="pb-2 pr-4">Leg ETA</th>
                    <th className="pb-2 pr-4">From start</th>
                    <th className="pb-2">Est. arrival</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {routeResult.stops.map((stop) => (
                    <tr key={stop.order_id} className="text-sm">
                      <td className="py-2.5 pr-4 font-semibold text-muted-foreground">
                        {stop.sequence}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{stop.order_id}</td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {stop.from_hub_name ?? '—'} → {stop.to_hub_name ?? '—'}
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                          {stop.eta_minutes} min
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-muted-foreground">
                        +{stop.eta_from_start_minutes} min
                      </td>
                      <td className="py-2.5 font-medium">{stop.estimated_arrival}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-border">
                    <td colSpan={3} className="pt-3 text-xs text-muted-foreground">
                      Total estimated time
                    </td>
                    <td colSpan={3} className="pt-3 text-right font-semibold">
                      {routeResult.total_eta_minutes} min
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ── All shipments history dialog ─────────────────────────────────── */}
      <Dialog open={allShipmentsOpen} onOpenChange={setAllShipmentsOpen}>
        <DialogContent className="flex max-h-[85vh] max-w-3xl flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle>All orders</DialogTitle>
            <DialogDescription>
              Every shipment on record — search by order ID, hub, city, courier, or delivery date.
            </DialogDescription>
          </DialogHeader>

          <div className="border-b border-border px-6 py-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={allShipmentsSearch}
                onChange={(e) => setAllShipmentsSearch(e.target.value)}
                placeholder="Search orders…"
                className="pl-10"
              />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-6 py-4">
            {allShipmentsLoading && (
              <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading all orders…
              </div>
            )}

            {!allShipmentsLoading && filteredAllShipments.length === 0 && (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No orders match your search.
              </p>
            )}

            {!allShipmentsLoading && filteredAllShipments.length > 0 && (
              <div className="space-y-2">
                {filteredAllShipments.map((shipment) => (
                  <div
                    key={shipment.order_id}
                    className="flex flex-col gap-3 rounded-xl border border-border bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-sm">{shipment.order_id}</p>
                        {shipment.delivery_day && (
                          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border">
                            {shipment.delivery_day}
                          </span>
                        )}
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                          {shipment.status ?? 'In Transit'}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {shipment.from_hub_name} → {shipment.to_hub_name}
                        {shipment.city_name ? ` · ${shipment.city_name}` : ''}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Courier:{' '}
                        {shipment.assigned_courier_name ??
                          shipment.assigned_courier_id ??
                          'Unassigned'}
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="gap-1"
                        onClick={() => {
                          setAllShipmentsOpen(false);
                          void handleShowShipmentOnMap(shipment);
                        }}
                      >
                        <MapPin className="h-3.5 w-3.5" />
                        Map
                      </Button>
                      {isManager && (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setAllShipmentsOpen(false);
                            void handleViewDetails(shipment.order_id);
                          }}
                        >
                          Details
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {!allShipmentsLoading && allShipments.length > 0 && (
            <div className="border-t border-border px-6 py-3 text-xs text-muted-foreground">
              Showing {filteredAllShipments.length} of {allShipments.length} orders
              {allShipments.length >= 200 ? ' (most recent 200)' : ''}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
