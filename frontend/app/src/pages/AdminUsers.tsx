import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import Navbar from '@/components/Navbar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { BadgeCheck, Search, ShieldCheck, UserPlus, Users } from 'lucide-react';

const users = [
  { id: 'USR-001', name: 'Priya Menon', role: 'Logistics Admin', team: 'Operations', status: 'Active', lastActive: '5 min ago', permissions: 'Full Access' },
  { id: 'USR-002', name: 'Amit Desai', role: 'Inventory Analyst', team: 'Inventory', status: 'Active', lastActive: '18 min ago', permissions: 'Read / Update' },
  { id: 'USR-003', name: 'Neha Kapoor', role: 'Compliance Lead', team: 'Risk', status: 'Review', lastActive: '34 min ago', permissions: 'Read Only' },
  { id: 'USR-004', name: 'Karthik Iyer', role: 'Dispatch Manager', team: 'Logistics', status: 'Pending', lastActive: '1h ago', permissions: 'Limited' },
  { id: 'USR-005', name: 'Rina Shah', role: 'Warehouse Supervisor', team: 'Warehouse', status: 'Active', lastActive: '2h ago', permissions: 'Read / Update' },
];

const statusClasses: Record<string, string> = {
  Active: 'bg-emerald-50 text-emerald-700',
  Pending: 'bg-amber-50 text-amber-700',
  Review: 'bg-sky-50 text-sky-700',
  Suspended: 'bg-red-50 text-red-700',
};

const roles = ['All roles', 'Logistics Admin', 'Inventory Analyst', 'Compliance Lead', 'Dispatch Manager', 'Warehouse Supervisor'];
const teams = ['All teams', 'Operations', 'Inventory', 'Risk', 'Logistics', 'Warehouse'];

export default function AdminUsers() {
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('All roles');
  const [teamFilter, setTeamFilter] = useState('All teams');

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const matchesQuery = user.name.toLowerCase().includes(query.toLowerCase()) || user.role.toLowerCase().includes(query.toLowerCase());
      const matchesRole = roleFilter === 'All roles' || user.role === roleFilter;
      const matchesTeam = teamFilter === 'All teams' || user.team === teamFilter;
      return matchesQuery && matchesRole && matchesTeam;
    });
  }, [query, roleFilter, teamFilter]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-6">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Admin center</p>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">User management</h1>
            <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
              Manage roles, permissions and collaboration access across teams aligned with enterprise governance.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              asChild
              className="inline-flex items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-slate-900"
            >
              <Link to="/register-user">
                <UserPlus className="h-4 w-4" /> Register user
              </Link>
            </Button>
            <Button variant="outline" className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium">
              <BadgeCheck className="h-4 w-4" /> Sync directory
            </Button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
              <div>
                <p className="text-sm font-semibold text-foreground">Team access</p>
                <p className="text-xs text-muted-foreground">Search users, filter by role, and review account status.</p>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <label className="block text-xs text-muted-foreground">
                  Role
                  <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} className="mt-2 w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary focus:ring-1 focus:ring-primary/20">
                    {roles.map((role) => (<option key={role}>{role}</option>))}
                  </select>
                </label>
                <label className="block text-xs text-muted-foreground">
                  Team
                  <select value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)} className="mt-2 w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary focus:ring-1 focus:ring-primary/20">
                    {teams.map((team) => (<option key={team}>{team}</option>))}
                  </select>
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search users"
                    className="pl-9"
                  />
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border text-left text-sm">
                <thead className="border-b border-border bg-background/70">
                  <tr>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Role</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Team</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Last Active</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Permissions</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-muted/80 transition-colors">
                      <td className="px-4 py-4">
                        <p className="font-semibold text-foreground">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.id}</p>
                      </td>
                      <td className="px-4 py-4 text-foreground">{user.role}</td>
                      <td className="px-4 py-4 text-muted-foreground">{user.team}</td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold ${statusClasses[user.status]}`}>{user.status}</span>
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">{user.lastActive}</td>
                      <td className="px-4 py-4 text-muted-foreground">{user.permissions}</td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-2">
                          <button className="rounded-full border border-border bg-muted px-3 py-1 text-xs text-muted-foreground transition hover:border-gray-300">Edit</button>
                          <button className="rounded-full border border-border bg-muted px-3 py-1 text-xs text-muted-foreground transition hover:border-gray-300">Reset</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Org access snapshot</p>
                  <p className="text-xs text-muted-foreground">Current breakdown by permission posture.</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-3xl bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Teams onboarded</p>
                    <p className="text-xs text-muted-foreground">6 cross-functional groups</p>
                  </div>
                  <span className="text-2xl font-semibold text-black">6</span>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-3xl bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Access reviews due</p>
                    <p className="text-xs text-muted-foreground">Next 7 days</p>
                  </div>
                  <span className="text-2xl font-semibold text-black">12</span>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-3xl bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Safety score</p>
                    <p className="text-xs text-muted-foreground">Role-based access maturity</p>
                  </div>
                  <span className="text-2xl font-semibold text-black">88%</span>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <Users className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Quick actions</p>
                  <p className="text-xs text-muted-foreground">Manage common workflows faster.</p>
                </div>
              </div>
              <div className="space-y-3">
                <button className="w-full rounded-2xl bg-black px-4 py-3 text-sm font-medium text-white transition hover:bg-slate-900">Review pending invites</button>
                <button className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm font-medium text-foreground transition hover:border-gray-300">Audit role assignments</button>
                <button className="w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm font-medium text-foreground transition hover:border-gray-300">Generate compliance report</button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
