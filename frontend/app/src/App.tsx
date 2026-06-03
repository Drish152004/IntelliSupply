import { Navigate, Route, Routes } from 'react-router';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Profile from './pages/Profile';
import Overview from './pages/Overview';
import Inventory from './pages/Inventory';
import InventoryAnalytics from './pages/InventoryAnalytics';
import LogisticsDashboard from './pages/Home';
import RouteIntelligence from './pages/RouteIntelligence';
import AdminUsers from './pages/AdminUsers';
import AdminAnalytics from './pages/AdminAnalytics';
import Notifications from './pages/Notifications';
import RegisterUser from './pages/RegisterUser';
import ProductManagement from './pages/ProductManagement';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/login/:role" element={<Login />} />

      <Route path="/logistics" element={<LogisticsDashboard />} />
      <Route path="/logistics/intelligence" element={<RouteIntelligence />} />

      <Route path="/product-management" element={<ProductManagement />} />
      <Route path="/inventory" element={<Inventory />} />
      <Route path="/inventory/analytics" element={<InventoryAnalytics />} />

      <Route path="/register-user" element={<RegisterUser />} />
      <Route path="/admin/dashboard" element={<Overview />} />
      <Route path="/admin/users" element={<AdminUsers />} />
      <Route path="/admin/analytics" element={<AdminAnalytics />} />

      <Route path="/profile" element={<Profile />} />
      <Route path="/notifications" element={<Notifications />} />

      <Route path="/routes" element={<Navigate to="/logistics" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
