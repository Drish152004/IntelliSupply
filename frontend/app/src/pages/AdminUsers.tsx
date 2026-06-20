import { useEffect, useMemo, useState } from 'react';
import { useSessionStorageState } from '@/hooks/useSessionStorage';
import { Link } from 'react-router';
import Navbar from '@/components/Navbar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { BadgeCheck, Search, ShieldCheck, UserPlus, Users } from 'lucide-react';
import { listUsers, type AdminUserRecord } from '@/lib/api';

const statusClasses: Record<string, string> = {
  Active: 'bg-emerald-50 text-emerald-700',
  Inactive: 'bg-red-50 text-red-700',
};

export default function AdminUsers() {
  const [query, setQuery] = useSessionStorageState('admin_users_query', '');
  const [roleFilter, setRoleFilter] = useSessionStorageState('admin_users_role_filter', 'All roles');
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load users.'))
      .finally(() => setLoading(false));
  }, []);

  const roles = useMemo(
    () => [
      'All roles',
      ...Array.from(new Set(users.map((user) => user.role).filter((role): role is string => Boolean(role)))).sort(),
    ],
    [users],
  );

  const filteredUsers = useMemo(() => {
    const normalizedQuery = query.toLowerCase();
    return users.filter((user) => {
      const name = (user.name ?? '').toLowerCase();
      const email = (user.email ?? '').toLowerCase();
      const role = (user.role ?? '').toLowerCase();
      const matchesQuery =
        name.includes(normalizedQuery) ||
        email.includes(normalizedQuery) ||
        role.includes(normalizedQuery);
      const matchesRole = roleFilter === 'All roles' || user.role === roleFilter;
      return matchesQuery && matchesRole;
    });
  }, [query, roleFilter, users]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-6">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Admin center</p>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">User management</h1>
            <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
              Live directory of Profile and Courier accounts from Neo4j.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild className="inline-flex items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-slate-900">
              <Link to="/register-user">
                <UserPlus className="h-4 w-4" /> Register user
              </Link>
            </Button>
            <Button variant="outline" className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium" onClick={() => window.location.reload()}>
              <BadgeCheck className="h-4 w-4" /> Refresh directory
            </Button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="app-panel-lg p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Team access</p>
                <p className="text-xs text-muted-foreground">Search users and filter by role.</p>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="block text-xs text-muted-foreground">
                  Role
                  <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} className="mt-2 w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary focus:ring-1 focus:ring-primary/20">
                    {roles.map((role) => (<option key={role}>{role}</option>))}
                  </select>
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search users" className="pl-9" />
                </div>
              </div>
            </div>

            {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
            {loading && <p className="mb-4 text-sm text-muted-foreground">Loading users...</p>}

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="border-b border-border bg-background/70">
                  <tr>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Email</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Role</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Type</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUsers.map((user) => {
                    const status = user.is_active === false ? 'Inactive' : 'Active';
                    return (
                      <tr key={`${user.account_type}-${user.id}`} className="hover:bg-muted/80 transition-colors">
                        <td className="px-4 py-4">
                          <p className="font-semibold text-foreground">{user.name ?? 'Unnamed user'}</p>
                          <p className="text-xs text-muted-foreground">{user.id ?? '—'}</p>
                        </td>
                        <td className="px-4 py-4 text-muted-foreground">{user.email ?? '—'}</td>
                        <td className="px-4 py-4 text-foreground">{user.role ?? '—'}</td>
                        <td className="px-4 py-4 text-muted-foreground">{user.account_type ?? 'Profile'}</td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold ${statusClasses[status]}`}>{status}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="app-panel-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Org access snapshot</p>
                  <p className="text-xs text-muted-foreground">Current directory totals.</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-3xl bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Accounts loaded</p>
                    <p className="text-xs text-muted-foreground">Profiles and couriers</p>
                  </div>
                  <span className="text-2xl font-semibold text-black">{users.length}</span>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-3xl bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Active accounts</p>
                    <p className="text-xs text-muted-foreground">Currently enabled</p>
                  </div>
                  <span className="text-2xl font-semibold text-black">{users.filter((user) => user.is_active !== false).length}</span>
                </div>
              </div>
            </div>

            <div className="app-panel-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <Users className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Quick actions</p>
                  <p className="text-xs text-muted-foreground">Manage common workflows faster.</p>
                </div>
              </div>
              <div className="space-y-3">
                <Button asChild className="w-full rounded-2xl bg-black px-4 py-3 text-sm font-medium text-white transition hover:bg-slate-900">
                  <Link to="/register-user">Register new user</Link>
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
