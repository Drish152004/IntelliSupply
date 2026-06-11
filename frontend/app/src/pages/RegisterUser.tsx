import { useState, type ElementType } from 'react';
import Navbar from '@/components/Navbar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  UserPlus,
  ShieldCheck,
  Truck,
  Package,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MapPin,
} from 'lucide-react';
import { registerUser, createCourierFrontend } from '@/lib/api';

type UserType = 'logistics_manager' | 'inventory_manager' | 'courier';

const USER_TYPE_CONFIG: Record<UserType, { label: string; icon: ElementType; color: string; description: string }> = {
  logistics_manager: {
    label: 'Logistics Manager',
    icon: Truck,
    color: 'border-sky-200 bg-sky-50 text-sky-900',
    description: 'Access to logistics dashboard, shipment operations, route intelligence.',
  },
  inventory_manager: {
    label: 'Inventory Manager',
    icon: Package,
    color: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    description: 'Access to inventory, product management, and stock analytics.',
  },
  courier: {
    label: 'Courier',
    icon: MapPin,
    color: 'border-amber-200 bg-amber-50 text-amber-900',
    description: 'Field courier registered in GraphDB with hub and city assignment.',
  },
};

export default function RegisterUser() {
  const [userType, setUserType] = useState<UserType>('logistics_manager');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Courier-only fields
  const [hubName, setHubName] = useState('');
  const [cityName, setCityName] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showCourierModal, setShowCourierModal] = useState(false);

  const config = USER_TYPE_CONFIG[userType];

  const resetForm = () => {
    setName('');
    setEmail('');
    setPassword('');
    setHubName('');
    setCityName('');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (userType === 'courier') {
      // Open courier modal for additional fields
      setShowCourierModal(true);
      return;
    }

    setSubmitting(true);
    try {
      await registerUser({ name, email, password, role: userType });
      setSuccess(`${config.label} "${name}" registered successfully.`);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCourierSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createCourierFrontend({ name, email, password, hub_name: hubName, city_name: cityName });
      setSuccess(`Courier "${name}" created and assigned to ${hubName} — ${cityName}.`);
      setShowCourierModal(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Courier creation failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <section className="mb-7">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground mb-1.5">
            User onboarding
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">Add user</h1>
          <p className="max-w-2xl mt-2 text-sm leading-6 text-muted-foreground">
            Create and provision users for logistics operations, inventory management, or field courier roles.
          </p>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          {/* LEFT — Form */}
          <section className="rounded-[2rem] border border-border bg-white p-6 shadow-sm space-y-6">
            {/* User type selector */}
            <div>
              <p className="text-sm font-semibold text-foreground mb-3">User type</p>
              <div className="grid grid-cols-3 gap-3">
                {(Object.entries(USER_TYPE_CONFIG) as [UserType, typeof USER_TYPE_CONFIG[UserType]][]).map(([type, cfg]) => {
                  const Ico = cfg.icon;
                  const isSelected = userType === type;
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => { setUserType(type); setError(null); setSuccess(null); }}
                      className={`flex flex-col items-center gap-2 rounded-2xl border-2 p-4 text-center transition ${
                        isSelected
                          ? cfg.color + ' border-opacity-80'
                          : 'border-border bg-white text-foreground hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <Ico className="h-5 w-5" />
                      <span className="text-xs font-semibold leading-tight">{cfg.label}</span>
                    </button>
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">{config.description}</p>
            </div>

            {/* Form fields */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex items-center gap-3 mb-1">
                <UserPlus className="h-5 w-5 text-slate-600" />
                <p className="text-sm font-semibold text-foreground">User information</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Full name</label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter full name"
                    required
                    className="rounded-2xl"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Work email</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="employee@company.com"
                    required
                    className="rounded-2xl"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-xs text-muted-foreground mb-1.5 block">Password</label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Set initial password"
                    required
                    className="rounded-2xl"
                  />
                </div>
              </div>

              {(error && !showCourierModal) && (
                <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{success}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full px-5"
                  onClick={resetForm}
                >
                  Reset
                </Button>
                <Button
                  type="submit"
                  disabled={submitting}
                  className="rounded-full bg-black px-6 text-white"
                >
                  {submitting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <UserPlus className="mr-2 h-4 w-4" />
                  )}
                  {userType === 'courier' ? 'Continue →' : 'Register User'}
                </Button>
              </div>
            </form>
          </section>

          {/* RIGHT — Summary */}
          <aside className="space-y-5">
            <div className="rounded-[2rem] border border-border bg-white p-5 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-semibold">Access summary</p>
                  <p className="text-xs text-muted-foreground">Permission preview</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="rounded-2xl bg-slate-50 p-3.5">
                  <p className="text-xs font-semibold text-foreground">User type</p>
                  <p className="mt-1 text-sm text-muted-foreground">{config.label}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-3.5">
                  <p className="text-xs font-semibold text-foreground">Dashboard access</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {userType === 'logistics_manager'
                      ? 'Logistics, Notifications'
                      : userType === 'inventory_manager'
                      ? 'Inventory, Notifications'
                      : 'Field operations only (no dashboard)'}
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-3.5">
                  <p className="text-xs font-semibold text-foreground">Storage</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {userType === 'courier' ? 'Neo4j AuraDB — Courier node' : 'Neo4j AuraDB — Profile node'}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-border bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold text-foreground mb-3">Onboarding notes</p>
              <div className="space-y-2">
                {['Credentials set on creation', 'Session active on first login', 'Role enforced via RBAC'].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-xl border border-border px-3.5 py-2.5 text-xs text-muted-foreground">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* Courier extra fields modal */}
      <Dialog open={showCourierModal} onOpenChange={setShowCourierModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-amber-600" />
              Courier assignment
            </DialogTitle>
            <DialogDescription>
              Assign hub and city for <strong>{name || 'this courier'}</strong>. Must match existing GraphDB Hub and City nodes.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCourierSubmit} className="space-y-4 mt-2">
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">Hub name</label>
              <Input
                value={hubName}
                onChange={(e) => setHubName(e.target.value)}
                placeholder="e.g. Hub_1"
                required
                className="rounded-2xl"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">City</label>
              <Input
                value={cityName}
                onChange={(e) => setCityName(e.target.value)}
                placeholder="e.g. Chongqing"
                required
                className="rounded-2xl"
              />
            </div>

            <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-800">
              Hub and city must already exist in the GraphDB. Courier will be linked via ASSIGNED_TO_HUB and OPERATES_IN relationships.
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" className="rounded-full" onClick={() => setShowCourierModal(false)}>
                Back
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full bg-black text-white">
                {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <MapPin className="mr-2 h-4 w-4" />}
                Create Courier
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}