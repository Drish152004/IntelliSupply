// src/pages/ProductManagement.tsx

import { useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';

import {
  Search,
  Plus,
  Pencil,
  Trash2,
  Package2,
  ChevronDown,
  AlertTriangle,
  Boxes,
  TrendingUp,
} from 'lucide-react';

const initialProducts = [
  {
    id: 'PRD-001',
    name: 'USB-C Hub 7-in-1',
    sku: 'ELX-7781',
    category: 'Electronics',
    stock: 12,
    price: '₹2,999',
    status: 'Low Stock',
    updated: '2h ago',
  },
  {
    id: 'PRD-002',
    name: 'Warehouse Scanner',
    sku: 'WHS-1120',
    category: 'Warehouse',
    stock: 84,
    price: '₹12,400',
    status: 'Healthy',
    updated: '30 min ago',
  },
  {
    id: 'PRD-003',
    name: 'Compression T-Shirt',
    sku: 'APP-8821',
    category: 'Apparel',
    stock: 214,
    price: '₹899',
    status: 'Healthy',
    updated: '4h ago',
  },
  {
    id: 'PRD-004',
    name: 'Vitamin C Tablets',
    sku: 'MED-1192',
    category: 'Medical',
    stock: 0,
    price: '₹599',
    status: 'Out of Stock',
    updated: '1d ago',
  },
  {
    id: 'PRD-005',
    name: 'Laptop Stand Pro',
    sku: 'ACS-9921',
    category: 'Accessories',
    stock: 32,
    price: '₹1,499',
    status: 'Low Stock',
    updated: '5h ago',
  },
  {
    id: 'PRD-006',
    name: 'Barcode Printer',
    sku: 'WHS-7782',
    category: 'Warehouse',
    stock: 120,
    price: '₹8,999',
    status: 'Healthy',
    updated: '10 min ago',
  },
];

const categories = [
  'All',
  'Electronics',
  'Warehouse',
  'Apparel',
  'Medical',
  'Accessories',
];

const statuses = [
  'All',
  'Healthy',
  'Low Stock',
  'Out of Stock',
];

export default function ProductManagement() {
  const [products, setProducts] = useState(initialProducts);

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  const [selectedProduct, setSelectedProduct] = useState<any>(null);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesSearch =
        product.name.toLowerCase().includes(search.toLowerCase()) ||
        product.sku.toLowerCase().includes(search.toLowerCase());

      const matchesCategory =
        categoryFilter === 'All' ||
        product.category === categoryFilter;

      const matchesStatus =
        statusFilter === 'All' ||
        product.status === statusFilter;

      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [search, categoryFilter, statusFilter, products]);

  const deleteProduct = (id: string) => {
    setProducts((prev) => prev.filter((item) => item.id !== id));

    if (selectedProduct?.id === id) {
      setSelectedProduct(null);
    }
  };

  const totalProducts = products.length;

  const lowStockCount = products.filter(
    (p) => p.status === 'Low Stock',
  ).length;

  const outOfStockCount = products.filter(
    (p) => p.status === 'Out of Stock',
  ).length;

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <Navbar />

      <main className="max-w-[1750px] mx-auto px-6 lg:px-10 py-8">
        {/* HEADER */}
        <section className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between mb-8">
          <div>
            <p className="text-sm uppercase tracking-[0.28em] text-slate-500 mb-3">
              Product workspace
            </p>

            <h1 className="text-5xl font-semibold tracking-tight">
              Product management
            </h1>

            <p className="mt-4 text-lg text-slate-500 max-w-3xl leading-8">
              Manage product inventory, stock visibility, SKU operations and
              warehouse product data from one centralized workspace.
            </p>
          </div>

          <button className="inline-flex items-center justify-center gap-3 rounded-full bg-slate-950 px-7 py-4 text-base font-semibold text-white transition hover:scale-[1.01]">
            <Plus className="h-5 w-5" />
            Add product
          </button>
        </section>

        {/* TOP METRICS */}
        <section className="grid gap-5 md:grid-cols-3 mb-8">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  Total products
                </p>

                <h2 className="mt-3 text-4xl font-semibold">
                  {totalProducts}
                </h2>
              </div>

              <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-slate-100">
                <Package2 className="h-8 w-8 text-slate-700" />
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  Low stock items
                </p>

                <h2 className="mt-3 text-4xl font-semibold">
                  {lowStockCount}
                </h2>
              </div>

              <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-amber-50">
                <AlertTriangle className="h-8 w-8 text-amber-600" />
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  Healthy inventory
                </p>

                <h2 className="mt-3 text-4xl font-semibold">
                  {products.filter((p) => p.status === 'Healthy').length}
                </h2>
              </div>

              <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-emerald-50">
                <TrendingUp className="h-8 w-8 text-emerald-600" />
              </div>
            </div>
          </div>
        </section>

        {/* MAIN LAYOUT */}
        <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
          {/* LEFT */}
          <div className="rounded-[2rem] border border-slate-200 bg-white shadow-sm overflow-hidden">
            {/* TOOLBAR */}
            <div className="border-b border-slate-200 p-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                {/* SEARCH */}
                <div className="relative w-full xl:max-w-md">
                  <Search className="absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />

                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search products or SKU"
                    className="h-14 w-full rounded-full border border-slate-200 bg-slate-50 pl-14 pr-5 text-base outline-none transition focus:border-slate-400"
                  />
                </div>

                {/* FILTERS */}
                <div className="flex flex-wrap gap-3">
                  {/* CATEGORY */}
                  <div className="relative">
                    <select
                      value={categoryFilter}
                      onChange={(e) =>
                        setCategoryFilter(e.target.value)
                      }
                      className="h-14 appearance-none rounded-full border border-slate-200 bg-white px-5 pr-12 text-sm font-medium outline-none"
                    >
                      {categories.map((category) => (
                        <option key={category}>
                          {category}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  </div>

                  {/* STATUS */}
                  <div className="relative">
                    <select
                      value={statusFilter}
                      onChange={(e) =>
                        setStatusFilter(e.target.value)
                      }
                      className="h-14 appearance-none rounded-full border border-slate-200 bg-white px-5 pr-12 text-sm font-medium outline-none"
                    >
                      {statuses.map((status) => (
                        <option key={status}>
                          {status}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>
              </div>
            </div>

            {/* TABLE */}
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Product
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Category
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Stock
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Price
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Status
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Updated
                    </th>

                    <th className="px-6 py-5 text-sm font-semibold text-slate-500">
                      Actions
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {filteredProducts.map((product) => (
                    <tr
                      key={product.id}
                      onClick={() => setSelectedProduct(product)}
                      className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50"
                    >
                      {/* PRODUCT */}
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
                            <Package2 className="h-6 w-6 text-slate-700" />
                          </div>

                          <div>
                            <p className="text-base font-semibold text-slate-950">
                              {product.name}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                              {product.sku}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* CATEGORY */}
                      <td className="px-6 py-5">
                        <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
                          {product.category}
                        </span>
                      </td>

                      {/* STOCK */}
                      <td className="px-6 py-5">
                        <div>
                          <p className="text-base font-semibold text-slate-950">
                            {product.stock}
                          </p>

                          <div className="mt-3 h-2 w-28 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className={`h-full rounded-full ${
                                product.status === 'Out of Stock'
                                  ? 'bg-red-500 w-[8%]'
                                  : product.status === 'Low Stock'
                                  ? 'bg-amber-500 w-[35%]'
                                  : 'bg-emerald-500 w-[90%]'
                              }`}
                            />
                          </div>
                        </div>
                      </td>

                      {/* PRICE */}
                      <td className="px-6 py-5 text-base text-slate-700">
                        {product.price}
                      </td>

                      {/* STATUS */}
                      <td className="px-6 py-5">
                        <span
                          className={`rounded-full px-4 py-2 text-xs font-semibold ${
                            product.status === 'Healthy'
                              ? 'bg-emerald-50 text-emerald-700'
                              : product.status === 'Low Stock'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-red-50 text-red-700'
                          }`}
                        >
                          {product.status}
                        </span>
                      </td>

                      {/* UPDATED */}
                      <td className="px-6 py-5 text-sm text-slate-500">
                        {product.updated}
                      </td>

                      {/* ACTIONS */}
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <button className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white transition hover:bg-slate-100">
                            <Pencil className="h-4 w-4 text-slate-700" />
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteProduct(product.id);
                            }}
                            className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 transition hover:bg-red-100"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredProducts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-24">
                  <Boxes className="h-14 w-14 text-slate-300" />

                  <h2 className="mt-5 text-3xl font-semibold text-slate-900">
                    No products found
                  </h2>

                  <p className="mt-3 text-lg text-slate-500">
                    Try changing filters or search terms.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT SIDEBAR */}
          <aside className="space-y-6">
            {/* PRODUCT DETAILS */}
            <div className="rounded-[2rem] border border-slate-200 bg-white p-7 shadow-sm">
              {selectedProduct ? (
                <>
                  <div className="flex h-20 w-20 items-center justify-center rounded-[2rem] bg-slate-100">
                    <Package2 className="h-10 w-10 text-slate-700" />
                  </div>

                  <h2 className="mt-7 text-3xl font-semibold tracking-tight">
                    {selectedProduct.name}
                  </h2>

                  <p className="mt-3 text-base text-slate-500">
                    SKU • {selectedProduct.sku}
                  </p>

                  <div className="mt-8 space-y-4">
                    <div className="rounded-3xl bg-slate-50 p-5">
                      <p className="text-sm text-slate-500">
                        Category
                      </p>

                      <p className="mt-2 text-xl font-semibold">
                        {selectedProduct.category}
                      </p>
                    </div>

                    <div className="rounded-3xl bg-slate-50 p-5">
                      <p className="text-sm text-slate-500">
                        Inventory
                      </p>

                      <p className="mt-2 text-xl font-semibold">
                        {selectedProduct.stock} units
                      </p>
                    </div>

                    <div className="rounded-3xl bg-slate-50 p-5">
                      <p className="text-sm text-slate-500">
                        Product price
                      </p>

                      <p className="mt-2 text-xl font-semibold">
                        {selectedProduct.price}
                      </p>
                    </div>

                    <div className="rounded-3xl bg-slate-50 p-5">
                      <p className="text-sm text-slate-500">
                        Last updated
                      </p>

                      <p className="mt-2 text-xl font-semibold">
                        {selectedProduct.updated}
                      </p>
                    </div>
                  </div>

                  <div className="mt-8 flex gap-3">
                    <button className="flex-1 rounded-full border border-slate-200 bg-white px-5 py-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
                      Edit product
                    </button>

                    <button
                      onClick={() =>
                        deleteProduct(selectedProduct.id)
                      }
                      className="flex-1 rounded-full bg-red-50 px-5 py-4 text-sm font-semibold text-red-700 transition hover:bg-red-100"
                    >
                      Delete
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                  <div className="flex h-24 w-24 items-center justify-center rounded-[2rem] bg-slate-100">
                    <Package2 className="h-12 w-12 text-slate-400" />
                  </div>

                  <h2 className="mt-7 text-3xl font-semibold text-slate-900">
                    Product details
                  </h2>

                  <p className="mt-4 text-lg leading-8 text-slate-500">
                    Select a product from the table to view inventory and SKU details.
                  </p>
                </div>
              )}
            </div>

            {/* QUICK STATS */}

          </aside>
        </section>
      </main>
    </div>
  );
}