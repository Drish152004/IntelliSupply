import { motion } from 'framer-motion';
import { ArrowRight, Boxes, ShieldCheck, Truck } from 'lucide-react';
import { useNavigate } from 'react-router';

const roles = [
  {
    title: 'Inventory Manager',
    description: 'Warehouse inventory intelligence and stock monitoring.',
    icon: Boxes,
    color: 'from-sky-50 to-sky-100 border-sky-100',
    route: '/login/inventory',
  },
  {
    title: 'Logistics Head',
    description: 'Delivery orchestration and shipment operations.',
    icon: Truck,
    color: 'from-emerald-50 to-emerald-100 border-emerald-100',
    route: '/login/logistics',
  },
  {
    title: 'Administrator',
    description: 'Platform governance, analytics and enterprise control.',
    icon: ShieldCheck,
    color: 'from-amber-50 to-amber-100 border-amber-100',
    route: '/login/admin',
  },
    {
    title: 'Courier',
    description: 'Route execution, assigned deliveries, and real-time shipment updates.',
    icon: Truck,
    color: 'from-emerald-50 to-emerald-100 border-emerald-100',
    route: '/login/courier',
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#f5f7fb] overflow-hidden">
      <main className="max-w-[1400px] mx-auto px-6 lg:px-10 py-10">
        {/* HERO */}
        <section className="flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-5 py-2.5 shadow-sm">
              <span className="text-base font-semibold tracking-tight text-slate-900">
                Intelli<span className="text-sky-600">Supply</span>
              </span>
            </div>

            <h1 className="mt-7 text-4xl sm:text-5xl font-semibold tracking-tight text-slate-950 leading-[1.05] max-w-3xl">
              IntelliSupply
            </h1>

            <p className="mt-4 text-lg text-slate-600 font-medium">
              Operational intelligence for modern supply systems
            </p>
          </motion.div>
        </section>

        {/* ROLE CARDS */}
        <section className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {roles.map((role, index) => {
            const Icon = role.icon;

            return (
              <motion.div
                key={role.title}
                initial={{ opacity: 0, y: 32 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: index * 0.12,
                  duration: 0.5,
                }}
                whileHover={{ y: -8 }}
                className={`group relative overflow-hidden rounded-[2rem] border bg-gradient-to-b ${role.color} p-7 shadow-sm transition-all duration-300`}
              >
                <div className="flex flex-col items-center text-center h-full">
                  <div className="flex h-20 w-20 items-center justify-center rounded-[1.5rem] bg-white shadow-sm">
                    <Icon className="h-9 w-9 text-slate-900" />
                  </div>

                  <h2 className="mt-7 text-2xl font-semibold tracking-tight text-slate-950">
                    {role.title}
                  </h2>

                  <p className="mt-3 text-base leading-7 text-slate-600 max-w-sm">
                    {role.description}
                  </p>

                  <button
                    onClick={() => navigate(role.route)}
                    className="mt-8 inline-flex items-center justify-center gap-2.5 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition-all hover:scale-[1.02]"
                  >
                    Continue
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </section>
      </main>
    </div>
  );
}