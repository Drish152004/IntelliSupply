import { NavLink, useNavigate } from 'react-router';
import {
  Bell,
  ShieldCheck,
  Package,
  LayoutDashboard,
  Package2,
  UserCircle2,
  LogOut,
  UserPlus,
} from 'lucide-react';
import { useAuth, type AppRole } from '@/lib/auth';

// ─── Nav items per role ───────────────────────────────────────────────────────

const ALL_NAV_ITEMS = [
  { label: 'Dashboard', to: '/admin/dashboard', icon: LayoutDashboard, roles: ['admin'] as AppRole[] },
  { label: 'Logistics', to: '/logistics', icon: Package, roles: ['admin', 'logistics_manager'] as AppRole[] },
  { label: 'Products', to: '/product-management', icon: Package2, roles: ['admin', 'inventory_manager'] as AppRole[] },
  { label: 'Inventory', to: '/inventory', icon: ShieldCheck, roles: ['admin', 'inventory_manager'] as AppRole[] },
  { label: 'Add Users', to: '/admin/users', icon: UserPlus, roles: ['admin'] as AppRole[] },
  { label: 'Notifications', to: '/notifications', icon: Bell, roles: ['admin', 'logistics_manager', 'inventory_manager'] as AppRole[] },
];

const ROLE_LABELS: Record<AppRole, string> = {
  admin: 'Admin',
  logistics_manager: 'Logistics',
  inventory_manager: 'Inventory',
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = user
    ? ALL_NAV_ITEMS.filter((item) => item.roles.includes(user.role))
    : [];

  const handleLogout = () => {
    logout();
    navigate('/', { replace: true });
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur-xl shadow-sm">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-2.5 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-4">
          <NavLink
            to="/"
            className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-semibold tracking-tight text-white shadow-sm transition hover:bg-slate-800"
          >
            <span>Intelli</span>
            <span className="text-sky-300">Supply</span>
          </NavLink>

          <div className="flex items-center gap-2">
            {user && (
              <span className="rounded-full border border-border bg-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-600">
                {ROLE_LABELS[user.role]}
              </span>
            )}
            <span className="rounded-full border border-border bg-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-700">
              V2.1
            </span>
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] transition ${
                  isActive
                    ? 'bg-slate-950 text-white'
                    : 'bg-slate-900 text-white hover:bg-slate-800'
                }`
              }
            >
              <UserCircle2 className="h-3.5 w-3.5" />
              {user ? user.name.split(' ')[0] : 'Profile'}
            </NavLink>
            {user && (
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-700 transition hover:bg-red-50 hover:text-red-700"
              >
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </button>
            )}
          </div>
        </div>

        <nav className="flex w-full flex-wrap items-center gap-1.5 overflow-x-auto pb-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition whitespace-nowrap ${
                    isActive
                      ? 'bg-slate-950 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950'
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
