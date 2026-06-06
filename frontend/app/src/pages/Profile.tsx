import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  ShieldCheck,
  Bell,
  User,
  Lock,
  Mail,
  Phone,
  MapPin,
} from 'lucide-react';

export default function Profile() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <section className="mb-8">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">
            Account center
          </p>

          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            Profile settings
          </h1>

          <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
            Manage your profile information, account security, notifications,
            and workspace preferences.
          </p>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          {/* LEFT */}
          <section className="space-y-6">
            {/* Profile Card */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center gap-5">
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-slate-100 text-3xl font-semibold text-slate-700">
                  GP
                </div>

                <div className="flex-1">
                  <h2 className="text-2xl font-semibold text-foreground">
                    Gaury Patel
                  </h2>

                  <p className="text-muted-foreground mt-1">
                    Platform Administrator
                  </p>

                  <div className="mt-4 flex flex-wrap gap-3">
                    <span className="rounded-full bg-emerald-50 px-4 py-1 text-xs font-semibold text-emerald-700">
                      Active
                    </span>

                    <span className="rounded-full bg-sky-50 px-4 py-1 text-xs font-semibold text-sky-700">
                      Full Access
                    </span>
                  </div>
                </div>

                <Button className="rounded-full bg-black px-5 py-2 text-white">
                  Edit Profile
                </Button>
              </div>
            </div>

            {/* Personal Information */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-foreground">
                  Personal information
                </h3>

                <p className="text-sm text-muted-foreground mt-1">
                  Update your account and contact details.
                </p>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <label className="text-sm text-muted-foreground">
                    Full name
                  </label>

                  <Input
                    defaultValue="Gaury Patel"
                    className="mt-2 rounded-2xl"
                  />
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">
                    Email address
                  </label>

                  <Input
                    defaultValue="gaury@company.com"
                    className="mt-2 rounded-2xl"
                  />
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">
                    Phone number
                  </label>

                  <Input
                    defaultValue="+91 9876543210"
                    className="mt-2 rounded-2xl"
                  />
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">
                    Location
                  </label>

                  <Input
                    defaultValue="Hosur, India"
                    className="mt-2 rounded-2xl"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <Button className="rounded-full bg-black px-5 py-2 text-white">
                  Save Changes
                </Button>
              </div>
            </div>

            {/* Security */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-foreground">
                  Security
                </h3>

                <p className="text-sm text-muted-foreground mt-1">
                  Password and account protection settings.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-3xl bg-slate-50 p-4">
                  <div className="flex items-center gap-3">
                    <Lock className="h-5 w-5 text-slate-700" />

                    <div>
                      <p className="font-semibold text-foreground">
                        Password
                      </p>

                      <p className="text-sm text-muted-foreground">
                        Last updated 18 days ago
                      </p>
                    </div>
                  </div>

                  <Button variant="outline" className="rounded-full">
                    Reset
                  </Button>
                </div>

                <div className="flex items-center justify-between rounded-3xl bg-slate-50 p-4">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-emerald-600" />

                    <div>
                      <p className="font-semibold text-foreground">
                        Two-factor authentication
                      </p>

                      <p className="text-sm text-muted-foreground">
                        Enabled for your account
                      </p>
                    </div>
                  </div>

                  <Button variant="outline" className="rounded-full">
                    Configure
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* RIGHT */}
          <aside className="space-y-6">
            {/* Quick Access */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <User className="h-5 w-5 text-sky-600" />

                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Account summary
                  </p>

                  <p className="text-xs text-muted-foreground">
                    Current workspace access
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">Role</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Platform Administrator
                  </p>
                </div>

                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">Department</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Operations
                  </p>
                </div>

                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">Last login</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Today • 09:12 AM
                  </p>
                </div>
              </div>
            </div>

            {/* Notification Preferences */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <Bell className="h-5 w-5 text-amber-600" />

                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Notifications
                  </p>

                  <p className="text-xs text-muted-foreground">
                    Manage alert preferences
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {[
                  'Email alerts',
                  'Inventory warnings',
                  'Route updates',
                  'Security notifications',
                ].map((item) => (
                  <div
                    key={item}
                    className="flex items-center justify-between rounded-2xl border border-border px-4 py-3"
                  >
                    <span className="text-sm font-medium">{item}</span>

                    <div className="h-6 w-11 rounded-full bg-black relative">
                      <div className="absolute right-1 top-1 h-4 w-4 rounded-full bg-white" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}