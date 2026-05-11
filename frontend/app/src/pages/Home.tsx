import { useState } from 'react';
import Navbar from '@/components/Navbar';
import RouteMap from '@/components/RouteMap';
import ShipmentPanel from '@/components/ShipmentPanel';

export default function Home() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <ShipmentPanel selectedRouteId={selectedRouteId} onRouteSelect={handleRouteSelect} />
        <RouteMap selectedRouteId={selectedRouteId} onRouteSelect={handleRouteSelect} />
      </div>
    </div>
  );
}
