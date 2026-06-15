import type { ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router';
import { useAuth, ROLE_HOME, type AppRole } from '@/lib/auth';

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles: AppRole[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // ✅ Show loading UI (better UX)
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading...
      </div>
    );
  }

  // ✅ Not logged in → go to login
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // ✅ Role NOT allowed
  if (!allowedRoles.includes(user.role)) {
    const home = ROLE_HOME[user.role] ?? '/';

    // ✅ Prevent redirect loop
    if (home !== location.pathname) {
      return <Navigate to={home} replace />;
    }

    // ✅ Fallback UI (very important)
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <p className="text-lg font-semibold text-foreground">Access restricted</p>

        <p className="max-w-md text-sm text-muted-foreground">
          Your role ({user.role}) cannot open this page. Contact an administrator if you
          believe this is a mistake.
        </p>

        <Link
          to="/"
          className="rounded-full bg-slate-950 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Return home
        </Link>
      </div>
    );
  }

  // ✅ Allowed
  return <>{children}</>;
}