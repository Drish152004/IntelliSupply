import { Navigate } from 'react-router';
import { useAuth, ROLE_HOME, type AppRole } from '@/lib/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: AppRole[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  // Still rehydrating session — render nothing briefly
  if (loading) return null;

  // Not logged in
  if (!user) return <Navigate to="/login" replace />;

  // Logged in but wrong role
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={ROLE_HOME[user.role]} replace />;
  }

  return <>{children}</>;
}
