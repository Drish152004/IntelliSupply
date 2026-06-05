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

export interface Shipment {
  id: string;
  origin: string;
  destination: string;
  vehicleType: string;
  driver: string;
  eta: string;
  delayProbability: number;
  priority: 'high' | 'medium' | 'low';
  status: 'ontime' | 'delayed' | 'critical' | 'optimized';
  weather: string;
  routeId: string;
  shipmentType: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

export const locations: Location[] = [
  { id: 'loc-1', name: 'Bangalore Central WH', lat: 12.9716, lng: 77.5946, type: 'warehouse' },
  { id: 'loc-2', name: 'Chennai Port Hub', lat: 13.0827, lng: 80.2707, type: 'port' },
  { id: 'loc-3', name: 'Hyderabad Depot', lat: 17.3850, lng: 78.4867, type: 'hub' },
  { id: 'loc-4', name: 'Pune Distribution', lat: 18.5204, lng: 73.8567, type: 'warehouse' },
  { id: 'loc-5', name: 'Mumbai Logistics Park', lat: 19.0760, lng: 72.8777, type: 'port' },
  { id: 'loc-6', name: 'Coimbatore Supplier', lat: 11.0168, lng: 76.9558, type: 'supplier' },
  { id: 'loc-7', name: 'Kochi Customer Hub', lat: 9.9312, lng: 76.2673, type: 'customer' },
  { id: 'loc-8', name: 'Vizag Industrial Zone', lat: 17.6868, lng: 83.2185, type: 'supplier' },
  { id: 'loc-9', name: 'Nagpur Transit Hub', lat: 21.1458, lng: 79.0882, type: 'hub' },
  { id: 'loc-10', name: 'Ahmedabad Warehouse', lat: 23.0225, lng: 72.5714, type: 'warehouse' },
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

export const shipments: Shipment[] = [
  {
    id: 'SHP-78432',
    origin: 'Bangalore Central WH',
    destination: 'Chennai Port Hub',
    vehicleType: 'Refrigerated Truck',
    driver: 'Rajesh Kumar',
    eta: '4h 30m',
    delayProbability: 12,
    priority: 'high',
    status: 'ontime',
    weather: 'Clear, 28°C',
    routeId: 'RT-2847',
    shipmentType: 'Pharmaceuticals',
  },
  {
    id: 'SHP-78433',
    origin: 'Bangalore Central WH',
    destination: 'Hyderabad Depot',
    vehicleType: 'Container Truck',
    driver: 'Suresh Reddy',
    eta: '8h 15m',
    delayProbability: 35,
    priority: 'medium',
    status: 'delayed',
    weather: 'Light Rain, 24°C',
    routeId: 'RT-2848',
    shipmentType: 'Electronics',
  },
  {
    id: 'SHP-78434',
    origin: 'Pune Distribution',
    destination: 'Mumbai Logistics Park',
    vehicleType: 'Flatbed Truck',
    driver: 'Amit Patil',
    eta: '3h 45m',
    delayProbability: 8,
    priority: 'high',
    status: 'optimized',
    weather: 'Clear, 30°C',
    routeId: 'RT-2849',
    shipmentType: 'Steel Coils',
  },
  {
    id: 'SHP-78435',
    origin: 'Coimbatore Supplier',
    destination: 'Bangalore Central WH',
    vehicleType: 'Container Truck',
    driver: 'Venkatesh Iyer',
    eta: '6h 20m',
    delayProbability: 62,
    priority: 'high',
    status: 'critical',
    weather: 'Heavy Rain, 22°C',
    routeId: 'RT-2850',
    shipmentType: 'Auto Parts',
  },
  {
    id: 'SHP-78436',
    origin: 'Chennai Port Hub',
    destination: 'Kochi Customer Hub',
    vehicleType: 'Refrigerated Truck',
    driver: 'Thomas Mathew',
    eta: '10h 30m',
    delayProbability: 18,
    priority: 'medium',
    status: 'ontime',
    weather: 'Partly Cloudy, 29°C',
    routeId: 'RT-2851',
    shipmentType: 'Seafood Export',
  },
  {
    id: 'SHP-78437',
    origin: 'Vizag Industrial Zone',
    destination: 'Chennai Port Hub',
    vehicleType: 'Heavy Hauler',
    driver: 'Prasad Rao',
    eta: '14h 00m',
    delayProbability: 22,
    priority: 'low',
    status: 'delayed',
    weather: 'Thunderstorms, 26°C',
    routeId: 'RT-2852',
    shipmentType: 'Minerals',
  },
  {
    id: 'SHP-78438',
    origin: 'Nagpur Transit Hub',
    destination: 'Ahmedabad Warehouse',
    vehicleType: 'Container Truck',
    driver: 'Manoj Sharma',
    eta: '16h 45m',
    delayProbability: 15,
    priority: 'medium',
    status: 'ontime',
    weather: 'Clear, 32°C',
    routeId: 'RT-2853',
    shipmentType: 'Textiles',
  },
  {
    id: 'SHP-78439',
    origin: 'Bangalore Central WH',
    destination: 'Pune Distribution',
    vehicleType: 'Box Truck',
    driver: 'Deepak Joshi',
    eta: '12h 30m',
    delayProbability: 28,
    priority: 'medium',
    status: 'delayed',
    weather: 'Foggy, 20°C',
    routeId: 'RT-2854',
    shipmentType: 'Consumer Goods',
  },
];

export const quickActions = [
  'Add Order',
  'Create Shipment',
  'Optimize Routes',
  'Generate ETA Report',
  'Detect Delays',
  'Reassign Driver',
  'Simulate Traffic',
  'Risk Analysis',
];

export const suggestedPrompts = [
  'Optimize all delayed shipments',
  'Find fastest route',
  'Reduce fuel cost',
  'Predict traffic delays',
  'Add new shipment',
  'Show warehouse bottlenecks',
];

export const quickActionResponses: Record<string, string> = {
  'Add Order': 'New order form initialized. Please provide the origin, destination, and cargo details to proceed.',
  'Create Shipment': 'Shipment creation wizard started. I can auto-assign the nearest available driver. Should I proceed?',
  'Optimize Routes': 'Analyzing all active routes for efficiency improvements... Found 3 routes with 15-22% potential savings. Applying optimizations now.',
  'Generate ETA Report': 'Compiling ETA accuracy report for the last 24 hours... Current on-time performance is 87.3%, up 2.1% from yesterday.',
  'Detect Delays': 'Scanning weather and traffic data... 2 shipments at risk: SHP-78435 (Heavy Rain) and SHP-78433 (Road Construction).',
  'Reassign Driver': 'Available drivers in your network: Rajesh Kumar (Bangalore), Amit Patil (Pune), Manoj Sharma (Nagpur). Who should I reassign?',
  'Simulate Traffic': 'Traffic simulation running for Bangalore-Hyderabad corridor... Peak congestion expected at 6:00 PM. Suggesting alternate route via Kurnool.',
  'Risk Analysis': 'Comprehensive risk analysis complete. Top risks: Weather (32%), Traffic (28%), Vehicle Breakdown (15%). Mitigation strategies available.',
};

export const initialChatMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'Optimize deliveries for Bangalore region',
    timestamp: new Date(Date.now() - 3600000),
  },
  {
    id: 'msg-2',
    role: 'ai',
    content: 'I found 3 alternate routes that reduce total travel time by 18%. Route RT-2849 (Pune to Mumbai) has been auto-optimized with fuel savings of 12%. Would you like me to apply these changes?',
    timestamp: new Date(Date.now() - 3500000),
  },

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
  'Warehouse capacity at Bangalore Central at 91% - consider redistribution.',
];
