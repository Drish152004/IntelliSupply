import { Navigate, Route, Routes } from 'react-router';
import Overview from './pages/Overview';
import Inventory from './pages/Inventory';
import InventoryAnalytics from './pages/InventoryAnalytics';
import LogisticsDashboard from './pages/Home';
import RouteIntelligence from './pages/RouteIntelligence';
import AdminUsers from './pages/AdminUsers';
import AdminAnalytics from './pages/AdminAnalytics';
import Notifications from './pages/Notifications';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/logistics" element={<LogisticsDashboard />} />
      <Route path="/logistics/intelligence" element={<RouteIntelligence />} />
      <Route path="/inventory" element={<Inventory />} />
      <Route path="/inventory/analytics" element={<InventoryAnalytics />} />
      <Route path="/admin/dashboard" element={<Overview />} />
      <Route path="/admin/users" element={<AdminUsers />} />
      <Route path="/admin/analytics" element={<AdminAnalytics />} />
      <Route path="/notifications" element={<Notifications />} />
      <Route path="/routes" element={<Navigate to="/logistics" replace />} />
      <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
    </Routes>
  );
}
