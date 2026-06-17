export interface Location {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: 'warehouse' | 'supplier' | 'customer' | 'port' | 'hub';
}

export interface Route {
  id: string;
  origin: Location;
  destination: Location;
  waypoints?: [number, number][];
  eta: string;
  shipmentCount: number;
  delayRisk: number;
  priority: 'high' | 'medium' | 'low';
  status: 'ontime' | 'delayed' | 'critical' | 'optimized';
  driver: string;
  vehicleType: string;
  fuelEstimate: string;
  cargoType: string;
  routeType: 'primary' | 'alternate';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date | string;
}

export const locations: Location[] = [
  { id: 'loc-1', name: 'Bangalore Central Hub', lat: 12.9716, lng: 77.5946, type: 'hub' },
  { id: 'loc-2', name: 'Chennai Hub', lat: 13.0827, lng: 80.2707, type: 'hub' },
  { id: 'loc-3', name: 'Hyderabad Hub', lat: 17.3850, lng: 78.4867, type: 'hub' },
  { id: 'loc-4', name: 'Pune Hub', lat: 18.5204, lng: 73.8567, type: 'hub' },
  { id: 'loc-5', name: 'Mumbai Hub', lat: 19.0760, lng: 72.8777, type: 'hub' },
  { id: 'loc-6', name: 'Coimbatore Hub', lat: 11.0168, lng: 76.9558, type: 'hub' },
  { id: 'loc-7', name: 'Kochi Hub', lat: 9.9312, lng: 76.2673, type: 'hub' },
  { id: 'loc-8', name: 'Vizag Hub', lat: 17.6868, lng: 83.2185, type: 'hub' },
  { id: 'loc-9', name: 'Nagpur Hub', lat: 21.1458, lng: 79.0882, type: 'hub' },
  { id: 'loc-10', name: 'Ahmedabad Hub', lat: 23.0225, lng: 72.5714, type: 'hub' },
];

export const routes: Route[] = [
  {
    id: 'RT-2847',
    origin: locations[0],
    destination: locations[1],
    waypoints: [[12.9716, 77.5946], [12.5, 78.5], [13.0827, 80.2707]],
    eta: '4h 30m',
    shipmentCount: 24,
    delayRisk: 12,
    priority: 'high',
    status: 'ontime',
    driver: 'Rajesh Kumar',
    vehicleType: 'Refrigerated Truck',
    fuelEstimate: '78L',
    cargoType: 'Pharmaceuticals',
    routeType: 'primary',
  },
  {
    id: 'RT-2848',
    origin: locations[0],
    destination: locations[2],
    waypoints: [[12.9716, 77.5946], [13.5, 77.8], [14.2, 78.0], [15.5, 78.2], [17.3850, 78.4867]],
    eta: '8h 15m',
    shipmentCount: 18,
    delayRisk: 35,
    priority: 'medium',
    status: 'delayed',
    driver: 'Suresh Reddy',
    vehicleType: 'Container Truck',
    fuelEstimate: '142L',
    cargoType: 'Electronics',
    routeType: 'primary',
  },
  {
    id: 'RT-2849',
    origin: locations[3],
    destination: locations[4],
    waypoints: [[18.5204, 73.8567], [18.8, 72.5], [19.0760, 72.8777]],
    eta: '3h 45m',
    shipmentCount: 32,
    delayRisk: 8,
    priority: 'high',
    status: 'optimized',
    driver: 'Amit Patil',
    vehicleType: 'Flatbed Truck',
    fuelEstimate: '65L',
    cargoType: 'Steel Coils',
    routeType: 'primary',
  },
  {
    id: 'RT-2850',
    origin: locations[5],
    destination: locations[0],
    waypoints: [[11.0168, 76.9558], [11.5, 77.2], [12.2, 77.4], [12.9716, 77.5946]],
    eta: '6h 20m',
    shipmentCount: 15,
    delayRisk: 62,
    priority: 'high',
    status: 'critical',
    driver: 'Venkatesh Iyer',
    vehicleType: 'Container Truck',
    fuelEstimate: '110L',
    cargoType: 'Auto Parts',
    routeType: 'primary',
  },
  {
    id: 'RT-2851',
    origin: locations[1],
    destination: locations[6],
    waypoints: [[13.0827, 80.2707], [12.5, 79.5], [11.8, 78.2], [9.9312, 76.2673]],
    eta: '10h 30m',
    shipmentCount: 20,
    delayRisk: 18,
    priority: 'medium',
    status: 'ontime',
    driver: 'Thomas Mathew',
    vehicleType: 'Refrigerated Truck',
    fuelEstimate: '185L',
    cargoType: 'Seafood Export',
    routeType: 'primary',
  },
  {
    id: 'RT-2852',
    origin: locations[7],
    destination: locations[1],
    waypoints: [[17.6868, 83.2185], [16.5, 80.5], [14.5, 80.0], [13.0827, 80.2707]],
    eta: '14h 00m',
    shipmentCount: 40,
    delayRisk: 22,
    priority: 'low',
    status: 'delayed',
    driver: 'Prasad Rao',
    vehicleType: 'Heavy Hauler',
    fuelEstimate: '240L',
    cargoType: 'Minerals',
    routeType: 'primary',
  },
  {
    id: 'RT-2853',
    origin: locations[8],
    destination: locations[9],
    waypoints: [[21.1458, 79.0882], [21.5, 76.5], [22.0, 74.0], [23.0225, 72.5714]],
    eta: '16h 45m',
    shipmentCount: 28,
    delayRisk: 15,
    priority: 'medium',
    status: 'ontime',
    driver: 'Manoj Sharma',
    vehicleType: 'Container Truck',
    fuelEstimate: '290L',
    cargoType: 'Textiles',
    routeType: 'alternate',
  },
  {
    id: 'RT-2854',
    origin: locations[0],
    destination: locations[3],
    waypoints: [[12.9716, 77.5946], [13.5, 77.0], [15.0, 76.0], [16.5, 75.0], [17.5, 74.2], [18.5204, 73.8567]],
    eta: '12h 30m',
    shipmentCount: 22,
    delayRisk: 28,
    priority: 'medium',
    status: 'delayed',
    driver: 'Deepak Joshi',
    vehicleType: 'Box Truck',
    fuelEstimate: '195L',
    cargoType: 'Consumer Goods',
    routeType: 'alternate',
  },
];

export const suggestedPrompts = [
  'Optimize all delayed shipments',
  'Find fastest route',
  'Reduce fuel cost',
  'Predict traffic delays',
  'Add new shipment',
  'Show hub bottlenecks',
];

export const statsCards = [
  { label: 'Active Deliveries', value: '42', change: '+8%', positive: true },
  { label: 'Avg ETA', value: '9.2h', change: '-12%', positive: true },
  { label: 'Delayed Shipments', value: '3', change: '-2', positive: true },
  { label: 'Fuel Efficiency', value: '8.4 km/L', change: '+5%', positive: true },
  { label: 'Risk Score', value: 'Low', change: '-15%', positive: true },
];

export const aiInsights = [
  'Rain near Chennai may increase ETA by 12% for route RT-2852.',
  'Bangalore-Hyderabad corridor showing 35% higher traffic than usual.',
  'Fuel prices dropped 3% in Maharashtra - optimal refuel window.',
  'Hub capacity at Bangalore Central at 91% - consider redistribution.',
];
