import { NavLink } from 'react-router';
import { Bell, ShieldCheck, Package, Users, PieChart } from 'lucide-react';

const navItems = [
  { label: 'Logistics', to: '/logistics', icon: Package },
  { label: 'Inventory', to: '/inventory', icon: ShieldCheck },
  { label: 'Admin', to: '/admin/dashboard', icon: Users },
  { label: 'Notifications', to: '/notifications', icon: Bell },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur-xl shadow-sm">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-4">
          <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-base font-semibold tracking-tight text-white shadow-sm">
            <span>Intelli</span>
            <span className="text-sky-300">Supply</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-border bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-700">
              V2.1
            </span>
            <span className="rounded-full bg-slate-900 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white">
              Admin
            </span>
          </div>
        </div>

        <nav className="flex w-full flex-wrap items-center gap-2 overflow-x-auto pb-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition whitespace-nowrap ${
                    isActive
                      ? 'bg-slate-950 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
