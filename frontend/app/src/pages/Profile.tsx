import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ShieldCheck, Bell, User, Lock } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Platform Administrator',
  logistics_manager: 'Logistics Manager',
  inventory_manager: 'Inventory Manager',
  courier: 'Courier',
};

export default function Profile() {
  const { user, refreshUser, updateProfile } = useAuth();
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
  }, [user?.name]);

  const initials = useMemo(() => {
    if (!user?.name) return 'U';
    return user.name
      .split(' ')
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }, [user?.name]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setMessage(null);
    const result = await updateProfile({ name: name.trim() });
    setSaving(false);
    setMessage(result.success ? 'Profile updated successfully.' : result.message ?? 'Update failed.');
  };

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section className="mb-8">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">Account center</p>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Profile settings</h1>
          <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
            Manage your profile information and account details synced from the authenticated session.
          </p>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          <section className="space-y-6">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center gap-5">
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-slate-100 text-3xl font-semibold text-slate-700">
                  {initials}
                </div>

                <div className="flex-1">
                  <h2 className="text-2xl font-semibold text-foreground">{user.name}</h2>
                  <p className="text-muted-foreground mt-1">{ROLE_LABELS[user.role] ?? user.role}</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <span className="rounded-full bg-emerald-50 px-4 py-1 text-xs font-semibold text-emerald-700">Active</span>
                    <span className="rounded-full bg-sky-50 px-4 py-1 text-xs font-semibold text-sky-700">{user.role}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-foreground">Personal information</h3>
                <p className="text-sm text-muted-foreground mt-1">Update your account details.</p>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <label className="text-sm text-muted-foreground">Full name</label>
                  <Input value={name} onChange={(event) => setName(event.target.value)} className="mt-2 rounded-2xl" />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Email address</label>
                  <Input value={user.email} readOnly className="mt-2 rounded-2xl bg-muted/40" />
                </div>
              </div>

              {message && <p className="mt-4 text-sm text-muted-foreground">{message}</p>}

              <div className="mt-6 flex justify-end">
                <Button className="rounded-full bg-black px-5 py-2 text-white" onClick={() => void handleSave()} disabled={saving}>
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-foreground">Security</h3>
                <p className="text-sm text-muted-foreground mt-1">JWT session authentication is active for API access.</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-3xl bg-slate-50 p-4">
                  <div className="flex items-center gap-3">
                    <Lock className="h-5 w-5 text-slate-700" />
                    <div>
                      <p className="font-semibold text-foreground">Password</p>
                      <p className="text-sm text-muted-foreground">Managed through your account provider</p>
                    </div>
                  </div>
                  <Button variant="outline" className="rounded-full" disabled>
                    Reset
                  </Button>
                </div>

                <div className="flex items-center justify-between rounded-3xl bg-slate-50 p-4">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-emerald-600" />
                    <div>
                      <p className="font-semibold text-foreground">JWT access token</p>
                      <p className="text-sm text-muted-foreground">Bearer token attached to API requests</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <User className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Account summary</p>
                  <p className="text-xs text-muted-foreground">Current workspace access</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">Role</p>
                  <p className="text-sm text-muted-foreground mt-1">{ROLE_LABELS[user.role] ?? user.role}</p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">User ID</p>
                  <p className="text-sm text-muted-foreground mt-1">{user.id ?? '—'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <Bell className="h-5 w-5 text-amber-600" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Notifications</p>
                  <p className="text-xs text-muted-foreground">Operational alerts are available on the notifications page</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
