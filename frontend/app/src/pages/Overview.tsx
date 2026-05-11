import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router';
import { Package, Truck, Brain, TrendingUp, Clock, Users } from 'lucide-react';

const kpiCards = [
  {
    label: 'Total Deliveries',
    value: '2,847',
    subtitle: 'This month',
    icon: Package,
    color: 'bg-black',
    trend: '↑ 12.4%',
  },
  {
    label: 'Avg Delivery Delay',
    value: '2.3 hrs',
    subtitle: 'Network average',
    icon: Clock,
    color: 'bg-gray-800',
    trend: '↓ 4.1%',
  },
  {
    label: 'Active Couriers',
    value: '142',
    subtitle: 'On active routes',
    icon: Users,
    color: 'bg-gray-700',
    trend: '↑ 8 new',
  },
  {
    label: 'Inventory Turnover',
    value: '4.2x',
    subtitle: 'Annual rate',
    icon: TrendingUp,
    color: 'bg-gray-900',
    trend: '↑ 2.1%',
  },
];

const navigationBoxes = [
  {
    title: 'Inventory',
    description: 'Manage stock levels, track products, and optimize warehouse operations',
    icon: Package,
    color: 'from-gray-800 to-gray-700',
    path: '/inventory',
  },
  {
    title: 'Logistics',
    description: 'Optimize routes, track deliveries, and manage courier performance',
    icon: Truck,
    color: 'from-gray-900 to-gray-800',
    path: '/routes',
  },
  {
    title: 'AI Copilot',
    description: 'Get intelligent insights and recommendations for supply chain operations',
    icon: Brain,
    color: 'from-black to-gray-900',
    path: '/copilot',
  },
];

export default function Overview() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white text-black">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-8 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-4xl font-bold text-black mb-2">Supply Chain Dashboard</h1>
          <p className="text-gray-600">Real-time overview of your logistics operations</p>
        </motion.div>

        {/* KPI Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12"
        >
          {kpiCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + idx * 0.05 }}
                className="border border-gray-200 rounded-xl p-6 bg-white hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-sm font-medium text-gray-600 uppercase tracking-wide mb-1">
                      {card.label}
                    </p>
                    <h3 className="text-3xl font-bold text-black">{card.value}</h3>
                  </div>
                  <div className={`${card.color} p-3 rounded-lg`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div className="flex items-end justify-between">
                  <p className="text-xs text-gray-500">{card.subtitle}</p>
                  <span className="text-xs font-semibold text-green-600">{card.trend}</span>
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Navigation Boxes */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold text-black mb-6">Quick Access</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {navigationBoxes.map((box, idx) => {
              const Icon = box.icon;
              return (
                <motion.button
                  key={box.title}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 + idx * 0.1 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => navigate(box.path)}
                  className={`relative group overflow-hidden rounded-xl h-48 text-white transition-all`}
                >
                  {/* Background gradient */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${box.color}`} />
                  
                  {/* Overlay on hover */}
                  <div className="absolute inset-0 bg-black/10 group-hover:bg-black/20 transition-colors" />
                  
                  {/* Content */}
                  <div className="relative z-10 p-6 h-full flex flex-col justify-between">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-2xl font-bold mb-2 text-white">{box.title}</h3>
                        <p className="text-sm text-gray-100 text-left leading-relaxed">
                          {box.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-sm font-medium">Explore</span>
                      <span className="text-lg">→</span>
                    </div>
                  </div>
                  
                  {/* Icon background */}
                  <Icon className="absolute bottom--10 right--10 w-40 h-40 text-white opacity-10 group-hover:opacity-20 transition-opacity" />
                </motion.button>
              );
            })}
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="border border-gray-200 rounded-xl p-6 bg-gray-50">
            <p className="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3">
              On-Time Delivery Rate
            </p>
            <div className="flex items-center gap-3">
              <span className="text-3xl font-bold text-black">92.4%</span>
              <span className="text-sm text-green-600 font-semibold">↑ 3.2%</span>
            </div>
            <div className="mt-4 w-full bg-gray-300 rounded-full h-2">
              <div className="bg-black h-2 rounded-full" style={{ width: '92.4%' }}></div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-xl p-6 bg-gray-50">
            <p className="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3">
              Network Throughput
            </p>
            <div className="flex items-center gap-3">
              <span className="text-3xl font-bold text-black">12,840</span>
              <span className="text-sm text-gray-600 font-semibold">shipments/week</span>
            </div>
            <p className="mt-3 text-xs text-gray-600">Operating at 94% capacity</p>
          </div>

          <div className="border border-gray-200 rounded-xl p-6 bg-gray-50">
            <p className="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3">
              Cost Efficiency
            </p>
            <div className="flex items-center gap-3">
              <span className="text-3xl font-bold text-black">₹1.28Cr</span>
              <span className="text-sm text-green-600 font-semibold">↓ 4.1%</span>
            </div>
            <p className="mt-3 text-xs text-gray-600">vs last month</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
