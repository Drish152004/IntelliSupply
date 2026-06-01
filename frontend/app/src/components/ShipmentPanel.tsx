import { useState, useMemo } from 'react';
import {
  Package,
  Plus,
  Filter,
  MapPin,
  Clock,
  AlertTriangle,
  TrendingUp,
  Cloud,
  Truck,
  User,
  Pencil,
  Trash2,
  ArrowUpCircle,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { shipments } from '@/data/mockData';
import type { Shipment } from '@/data/mockData';

interface ShipmentPanelProps {
  selectedRouteId: string | null;
  onRouteSelect: (routeId: string) => void;
}

export default function ShipmentPanel({ selectedRouteId, onRouteSelect }: ShipmentPanelProps) {
  const [filters, setFilters] = useState({
    priority: 'all',
    status: 'all',
    delayRisk: 'all',
  });
  const [showFilters, setShowFilters] = useState(false);

  const filteredShipments = useMemo(() => {
    return shipments.filter((s) => {
      if (filters.priority !== 'all' && s.priority !== filters.priority) return false;
      if (filters.status !== 'all' && s.status !== filters.status) return false;
      if (filters.delayRisk === 'high' && s.delayProbability < 30) return false;
      if (filters.delayRisk === 'low' && s.delayProbability >= 30) return false;
      return true;
    });
  }, [filters]);

  const getStatusStyles = (status: Shipment['status']) => {
    switch (status) {
      case 'ontime':
        return 'status-ontime';
      case 'delayed':
        return 'status-delayed';
      case 'critical':
        return 'status-critical';
      case 'optimized':
        return 'status-optimized';
    }
  };

  const getPriorityColor = (priority: Shipment['priority']) => {
    switch (priority) {
      case 'high':
        return 'text-red-500';
      case 'medium':
        return 'text-amber-500';
      case 'low':
        return 'text-slate-400';
    }
  };

  const handleCardClick = (routeId: string) => {
    onRouteSelect(routeId);
  };

  return (
    <div className="w-80 border-r border-border bg-white flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="h-12 border-b border-border flex items-center justify-between px-4 shrink-0 bg-[#f8f9fa]">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-black" />
          <span className="text-sm font-medium">Shipments</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          </Button>
          <Button size="sm" className="h-7 text-[11px] gap-1 bg-black text-white hover:bg-black/90">
            <Plus className="w-3 h-3" />
            Add
          </Button>
        </div>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-b border-border"
          >
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-muted-foreground">Filters</span>
                <button onClick={() => setShowFilters(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="w-3 h-3" />
                </button>
              </div>
              <div className="flex flex-wrap gap-1">
                {['all', 'high', 'medium', 'low'].map((p) => (
                  <button
                    key={p}
                    onClick={() => setFilters((f) => ({ ...f, priority: p }))}
                    className={`text-[10px] px-2 py-1 rounded-md transition-colors ${
                      filters.priority === p
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {p === 'all' ? 'All Priority' : p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1">
                {['all', 'ontime', 'delayed', 'critical', 'optimized'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setFilters((f) => ({ ...f, status: s }))}
                    className={`text-[10px] px-2 py-1 rounded-md transition-colors ${
                      filters.status === s
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {s === 'all' ? 'All Status' : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1">
                {['all', 'high', 'low'].map((r) => (
                  <button
                    key={r}
                    onClick={() => setFilters((f) => ({ ...f, delayRisk: r }))}
                    className={`text-[10px] px-2 py-1 rounded-md transition-colors ${
                      filters.delayRisk === r
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {r === 'all' ? 'All Risk' : `${r.charAt(0).toUpperCase() + r.slice(1)} Risk`}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Shipment Cards */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2.5">
        <AnimatePresence>
          {filteredShipments.map((shipment, index) => (
            <motion.div
              key={shipment.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ delay: index * 0.05, duration: 0.25 }}
              onClick={() => handleCardClick(shipment.routeId)}
              className={`rounded-xl border p-3 cursor-pointer interactive-hover ${
                selectedRouteId === shipment.routeId
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-card hover:border-border/80'
              }`}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold">{shipment.id}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${getStatusStyles(shipment.status)}`}>
                    {shipment.status}
                  </span>
                </div>
                <TrendingUp className={`w-3.5 h-3.5 ${getPriorityColor(shipment.priority)}`} />
              </div>

              {/* Route */}
              <div className="flex items-center gap-2 mb-2">
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <MapPin className="w-3 h-3" />
                  <span className="truncate max-w-[80px]">{shipment.origin}</span>
                </div>
                <div className="flex-1 h-px bg-border" />
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <span className="truncate max-w-[80px]">{shipment.destination}</span>
                  <MapPin className="w-3 h-3" />
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 mb-2.5">
                <div className="flex items-center gap-1.5">
                  <Truck className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground truncate">{shipment.vehicleType}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <User className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground truncate">{shipment.driver}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">{shipment.eta}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">{shipment.delayProbability}% delay</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Cloud className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground truncate">{shipment.weather}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Package className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground truncate">{shipment.shipmentType}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1 bg-muted rounded-full overflow-hidden mb-2.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${100 - shipment.delayProbability}%` }}
                  transition={{ delay: 0.3, duration: 0.6, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    shipment.status === 'critical' ? 'bg-red-500' :
                    shipment.status === 'delayed' ? 'bg-amber-500' :
                    shipment.status === 'optimized' ? 'bg-blue-500' :
                    'bg-emerald-500'
                  }`}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 gap-1">
                  <Pencil className="w-3 h-3" />
                  Edit
                </Button>
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 gap-1 text-red-500 hover:text-red-600">
                  <Trash2 className="w-3 h-3" />
                  Delete
                </Button>
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 gap-1">
                  <ArrowUpCircle className="w-3 h-3" />
                  Priority
                </Button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
