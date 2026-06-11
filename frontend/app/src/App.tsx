import { Navigate, Route, Routes } from 'react-router';
import { AuthProvider } from '@/lib/auth';
import ProtectedRoute from '@/components/ProtectedRoute';
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
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/login/:role" element={<Login />} />

        {/* Admin only */}
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Overview />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/analytics"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AdminAnalytics />
            </ProtectedRoute>
          }
        />
        <Route
          path="/register-user"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <RegisterUser />
            </ProtectedRoute>
          }
        />

        {/* Logistics (admin + logistics_manager) */}
        <Route
          path="/logistics"
          element={
            <ProtectedRoute allowedRoles={['admin', 'logistics_manager']}>
              <LogisticsDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/logistics/intelligence"
          element={
            <ProtectedRoute allowedRoles={['admin', 'logistics_manager']}>
              <RouteIntelligence />
            </ProtectedRoute>
          }
        />

        {/* Inventory (admin + inventory_manager) */}
        <Route
          path="/inventory"
          element={
            <ProtectedRoute allowedRoles={['admin', 'inventory_manager']}>
              <Inventory />
            </ProtectedRoute>
          }
        />
        <Route
          path="/inventory/analytics"
          element={
            <ProtectedRoute allowedRoles={['admin', 'inventory_manager']}>
              <InventoryAnalytics />
            </ProtectedRoute>
          }
        />
        <Route
          path="/product-management"
          element={
            <ProtectedRoute allowedRoles={['admin', 'inventory_manager']}>
              <ProductManagement />
            </ProtectedRoute>
          }
        />

        {/* All authenticated roles */}
        <Route
          path="/profile"
          element={
            <ProtectedRoute allowedRoles={['admin', 'logistics_manager', 'inventory_manager', 'courier']}>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/notifications"
          element={
            <ProtectedRoute allowedRoles={['admin', 'logistics_manager', 'inventory_manager']}>
              <Notifications />
            </ProtectedRoute>
          }
        />

        {/* Redirects */}
        <Route path="/routes" element={<Navigate to="/logistics" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
