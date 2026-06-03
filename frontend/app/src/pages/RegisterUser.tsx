import { useState } from 'react';
import Navbar from '@/components/Navbar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  UserPlus,
  ShieldCheck,
  Mail,
  Phone,
  Building2,
  Briefcase,
} from 'lucide-react';

export default function RegisterUser() {
  const [role, setRole] = useState('Inventory Analyst');

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <section className="mb-8">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground mb-2">
            User onboarding
          </p>

          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            Register new user
          </h1>

          <p className="max-w-2xl mt-3 text-sm leading-6 text-muted-foreground">
            Create and provision new users across logistics, warehouse,
            inventory, and operations teams.
          </p>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          {/* LEFT */}
          <section className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <UserPlus className="h-6 w-6 text-slate-700" />

              <div>
                <h2 className="text-xl font-semibold">
                  User information
                </h2>

                <p className="text-sm text-muted-foreground">
                  Enter employee and workspace details.
                </p>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label className="text-sm text-muted-foreground">
                  Full name
                </label>

                <Input
                  placeholder="Enter full name"
                  className="mt-2 rounded-2xl"
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Work email
                </label>

                <Input
                  placeholder="employee@company.com"
                  className="mt-2 rounded-2xl"
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Phone number
                </label>

                <Input
                  placeholder="+91 9876543210"
                  className="mt-2 rounded-2xl"
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Employee ID
                </label>

                <Input
                  placeholder="EMP-1024"
                  className="mt-2 rounded-2xl"
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Department
                </label>

                <select className="mt-2 w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm">
                  <option>Operations</option>
                  <option>Inventory</option>
                  <option>Warehouse</option>
                  <option>Compliance</option>
                  <option>Logistics</option>
                </select>
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Role
                </label>

                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-2 w-full rounded-2xl border border-border bg-background px-4 py-3 text-sm"
                >
                  <option>Inventory Analyst</option>
                  <option>Warehouse Supervisor</option>
                  <option>Dispatch Manager</option>
                  <option>Logistics Admin</option>
                  <option>Compliance Lead</option>
                </select>
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                variant="outline"
                className="rounded-full px-5"
              >
                Cancel
              </Button>

              <Button className="rounded-full bg-black px-6 text-white">
                Register User
              </Button>
            </div>
          </section>

          {/* RIGHT */}
          <aside className="space-y-6">
            {/* Access Summary */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />

                <div>
                  <p className="text-sm font-semibold">
                    Access summary
                  </p>

                  <p className="text-xs text-muted-foreground">
                    Workspace permission preview
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">
                    Selected role
                  </p>

                  <p className="mt-1 text-sm text-muted-foreground">
                    {role}
                  </p>
                </div>

                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">
                    Default access
                  </p>

                  <p className="mt-1 text-sm text-muted-foreground">
                    Dashboard, inventory, analytics
                  </p>
                </div>

                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold">
                    MFA enforcement
                  </p>

                  <p className="mt-1 text-sm text-muted-foreground">
                    Enabled after activation
                  </p>
                </div>
              </div>
            </div>

            {/* Onboarding Notes */}
            <div className="rounded-[2rem] border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-5">
                <Briefcase className="h-5 w-5 text-sky-600" />

                <div>
                  <p className="text-sm font-semibold">
                    Onboarding notes
                  </p>

                  <p className="text-xs text-muted-foreground">
                    Internal provisioning workflow
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {[
                  'Directory sync after approval',
                  'Temporary password issued automatically',
                  'Email verification required',
                  'Security review pending',
                ].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-border px-4 py-3 text-sm"
                  >
                    {item}
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