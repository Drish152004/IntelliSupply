import { Navigate, Route, Routes } from 'react-router';
import { AuthProvider } from '@/lib/auth';
import ProtectedRoute from '@/components/ProtectedRoute';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Profile from './pages/Profile';
import Overview from './pages/Overview';
import Inventory from './pages/Inventory';
import LogisticsDashboard from './pages/Home';
import RouteIntelligence from './pages/RouteIntelligence';
import AdminUsers from './pages/AdminUsers';
import AdminAnalytics from './pages/AdminAnalytics';
import Notifications from './pages/Notifications';
import RegisterUser from './pages/RegisterUser';
import Planning from './pages/Planning';

// ✅ NEW: Courier page
import Courier from './pages/Courier';

export default function App() {
  return (
    <AuthProvider>
      <Routes>

        {/* ---------------- PUBLIC ---------------- */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/login/:role" element={<Login />} />

        {/* ---------------- ADMIN ---------------- */}
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

        {/* ---------------- LOGISTICS (FIXED ✅ removed courier) ---------------- */}
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

        {/* ---------------- INVENTORY ---------------- */}
        <Route
          path="/inventory"
          element={
            <ProtectedRoute allowedRoles={['admin', 'inventory_manager']}>
              <Inventory />
            </ProtectedRoute>
          }
        />

        <Route
          path="/planning"
          element={
            <ProtectedRoute allowedRoles={['admin', 'inventory_manager', 'logistics_manager']}>
              <Planning />
            </ProtectedRoute>
          }
        />

        {/* ---------------- COURIER (NEW ✅ separate dashboard) ---------------- */}
        <Route
          path="/courier"
          element={
            <ProtectedRoute allowedRoles={['courier']}>
              <Courier />
            </ProtectedRoute>
          }
        />

        {/* ---------------- COMMON (UNCHANGED ✅) ---------------- */}
        <Route
          path="/profile"
          element={
            <ProtectedRoute
              allowedRoles={[
                'admin',
                'logistics_manager',
                'inventory_manager',
                'courier',
              ]}
            >
              <Profile />
            </ProtectedRoute>
          }
        />

        {/* ✅ kept courier access to notifications (safe improvement) */}
        <Route
          path="/notifications"
          element={
            <ProtectedRoute
              allowedRoles={[
                'admin',
                'logistics_manager',
                'inventory_manager',
                'courier',
              ]}
            >
              <Notifications />
            </ProtectedRoute>
          }
        />

        {/* ---------------- REDIRECTS ---------------- */}
        <Route path="/routes" element={<Navigate to="/logistics" replace />} />
        <Route path="/product-management" element={<Navigate to="/inventory" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </AuthProvider>
  );
}