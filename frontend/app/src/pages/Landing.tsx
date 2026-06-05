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
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#f5f7fb] overflow-hidden">
      <main className="max-w-[1600px] mx-auto px-6 lg:px-12 py-16">
        {/* HERO */}
        <section className="flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: -24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-6 py-3 shadow-sm">
              <span className="text-lg font-semibold tracking-tight text-slate-900">
                Intelli<span className="text-sky-600">Supply</span>
              </span>
            </div>

            <h1 className="mt-10 text-6xl sm:text-7xl font-semibold tracking-tight text-slate-950 leading-[1.02] max-w-5xl">
              IntelliSupply
            </h1>

            <p className="mt-6 text-2xl text-slate-600 font-medium">
              Operational intelligence for modern supply systems
            </p>
          </motion.div>
        </section>

        {/* ROLE CARDS */}
        <section className="mt-24 grid gap-8 lg:grid-cols-3">
          {roles.map((role, index) => {
            const Icon = role.icon;

            return (
              <motion.div
                key={role.title}
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: index * 0.12,
                  duration: 0.55,
                }}
                whileHover={{
                  y: -10,
                }}
                className={`group relative overflow-hidden rounded-[2.5rem] border bg-gradient-to-b ${role.color} p-10 shadow-sm transition-all duration-300`}
              >
                <div className="flex flex-col items-center text-center h-full">
                  <div className="flex h-28 w-28 items-center justify-center rounded-[2rem] bg-white shadow-sm">
                    <Icon className="h-12 w-12 text-slate-900" />
                  </div>

                  <h2 className="mt-10 text-3xl font-semibold tracking-tight text-slate-950">
                    {role.title}
                  </h2>

                  <p className="mt-5 text-lg leading-8 text-slate-600 max-w-sm">
                    {role.description}
                  </p>

                  <button
                    onClick={() => navigate(role.route)}
                    className="mt-12 inline-flex items-center justify-center gap-3 rounded-full bg-slate-950 px-8 py-5 text-base font-semibold text-white transition-all hover:scale-[1.02]"
                  >
                    Continue
                    <ArrowRight className="h-5 w-5" />
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