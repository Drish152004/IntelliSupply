// src/pages/ProductManagement.tsx

import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

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
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  createInventoryProduct,
  deleteInventoryProduct,
  listInventoryProducts,
} from '@/lib/api';

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

// Categories matching the real products DB
const PRODUCT_CATEGORIES = [
  'Smartphones',
  'Laptops',
  'Tablets',
  'Wearables',
  'Audio Devices',
  'Accessories',
  'Smart Home',
  'XR Devices',
  'Electronics',
  'Warehouse',
  'Apparel',
  'Medical',
];

const categories = [
  'All',
  'Electronics',
  'Warehouse',
  'Apparel',
  'Medical',
  'Accessories',
  'Smartphones',
  'Laptops',
  'Tablets',
  'Wearables',
  'Audio Devices',
  'Smart Home',
  'XR Devices',
];

const statuses = [
  'All',
  'Healthy',
  'Low Stock',
  'Out of Stock',
];

// ─── Add Product form state type ─────────────────────────────────────────────

const EMPTY_FORM = {
  // products table fields
  product_name: '',
  category: 'Smartphones',
  unit_price: '',
  supplier_name: '',
  // inventory table fields
  quantity: '',
  threshold_limit: '',
  hub_id: '',
};

export default function ProductManagement() {
  const [products, setProducts] = useState(initialProducts);
  const [_loading, setLoading] = useState(true);

  useEffect(() => {
    void listInventoryProducts()
      .then((rows) =>
        setProducts(
          rows.map((product) => ({
            id: product.id,
            name: product.name,
            sku: product.id,
            category: product.category ?? 'General',
            stock: product.stock,
            price: product.unit_price ? `₹${product.unit_price.toLocaleString('en-IN')}` : '₹0',
            status: product.status,
            updated: 'Synced',
          })),
        ),
      )
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selectedProduct, setSelectedProduct] = useState<any>(null);

  // ─── Add Product modal state ────────────────────────────────────────────────
  const [showAddModal, setShowAddModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);

  const handleFormChange = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddSubmitting(true);
    setAddSuccess(false);

    try {
      const price = parseFloat(form.unit_price) || 0;
      const created = await createInventoryProduct({
        name: form.product_name,
        category: form.category,
        unit_price: price,
        supplier_name: form.supplier_name || undefined,
      });

      const newProduct = {
        id: created.id,
        name: created.name,
        sku: created.id,
        category: created.category ?? form.category,
        stock: created.stock,
        price: `₹${price.toLocaleString('en-IN')}`,
        status: created.status,
        updated: 'Just now',
        supplier_name: form.supplier_name,
        hub_id: form.hub_id,
        threshold_limit: parseInt(form.threshold_limit) || 0,
      };

      setProducts((prev) => [newProduct, ...prev]);
      setAddSuccess(true);
      setTimeout(() => {
        setShowAddModal(false);
        setAddSuccess(false);
        setForm(EMPTY_FORM);
      }, 1200);
    } finally {
      setAddSubmitting(false);
    }
  };

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

  const deleteProduct = async (id: string) => {
    try {
      await deleteInventoryProduct(id);
      setProducts((prev) => prev.filter((item) => item.id !== id));
    } catch {
      // ignore delete errors in UI for now
    }

    if (selectedProduct?.id === id) {
      setSelectedProduct(null);
    }
  };

  const totalProducts = products.length;

  const lowStockCount = products.filter(
    (p) => p.status === 'Low Stock',
  ).length;

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <Navbar />

      <main className="max-w-[1750px] mx-auto px-6 lg:px-10 py-8">
        {/* HEADER */}
        <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500 mb-2">
              Product workspace
            </p>

            <h1 className="text-3xl font-semibold tracking-tight">
              Product management
            </h1>

            <p className="mt-2 text-sm text-slate-500 max-w-3xl leading-6">
              Manage product inventory, stock visibility, SKU operations and
              warehouse product data from one centralized workspace.
            </p>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:scale-[1.01]"
          >
            <Plus className="h-4 w-4" />
            Add product
          </button>
        </section>

        {/* TOP METRICS */}
        <section className="grid gap-4 md:grid-cols-3 mb-6">
          <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">
                  Total products
                </p>
                <h2 className="mt-2 text-2xl font-semibold">
                  {totalProducts}
                </h2>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-[1.25rem] bg-slate-100">
                <Package2 className="h-6 w-6 text-slate-700" />
              </div>
            </div>
          </div>

          <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">
                  Low stock items
                </p>
                <h2 className="mt-2 text-2xl font-semibold">
                  {lowStockCount}
                </h2>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-[1.25rem] bg-amber-50">
                <AlertTriangle className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </div>

          <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">
                  Healthy inventory
                </p>
                <h2 className="mt-2 text-2xl font-semibold">
                  {products.filter((p) => p.status === 'Healthy').length}
                </h2>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-[1.25rem] bg-emerald-50">
                <TrendingUp className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </div>
        </section>

        {/* MAIN LAYOUT */}
        <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
          {/* LEFT */}
          <div className="rounded-[2rem] border border-slate-200 bg-white shadow-sm overflow-hidden">
            {/* TOOLBAR */}
            <div className="border-b border-slate-200 p-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                {/* SEARCH */}
                <div className="relative w-full xl:max-w-sm">
                  <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search products or SKU"
                    className="h-10 w-full rounded-full border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm outline-none transition focus:border-slate-400"
                  />
                </div>

                {/* FILTERS */}
                <div className="flex flex-wrap gap-2">
                  <div className="relative">
                    <select
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                      className="h-10 appearance-none rounded-full border border-slate-200 bg-white px-4 pr-9 text-sm font-medium outline-none"
                    >
                      {categories.map((category) => (
                        <option key={category}>{category}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>

                  <div className="relative">
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="h-10 appearance-none rounded-full border border-slate-200 bg-white px-4 pr-9 text-sm font-medium outline-none"
                    >
                      {statuses.map((status) => (
                        <option key={status}>{status}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>
              </div>
            </div>

            {/* TABLE */}
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Product</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Category</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Stock</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Price</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Updated</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredProducts.map((product) => (
                    <tr
                      key={product.id}
                      onClick={() => setSelectedProduct(product)}
                      className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100">
                            <Package2 className="h-5 w-5 text-slate-700" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-950">{product.name}</p>
                            <p className="text-xs text-slate-500">{product.sku}</p>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                          {product.category}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <p className="text-sm font-semibold text-slate-950">{product.stock}</p>
                        <div className="mt-1.5 h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
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
                      </td>

                      <td className="px-4 py-3 text-sm text-slate-700">{product.price}</td>

                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
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

                      <td className="px-4 py-3 text-xs text-slate-500">{product.updated}</td>

                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white transition hover:bg-slate-100">
                            <Pencil className="h-3.5 w-3.5 text-slate-700" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteProduct(product.id);
                            }}
                            className="flex h-8 w-8 items-center justify-center rounded-full bg-red-50 transition hover:bg-red-100"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-red-600" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredProducts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16">
                  <Boxes className="h-10 w-10 text-slate-300" />
                  <h2 className="mt-4 text-xl font-semibold text-slate-900">No products found</h2>
                  <p className="mt-2 text-sm text-slate-500">Try changing filters or search terms.</p>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT SIDEBAR */}
          <aside className="space-y-6">
            {/* PRODUCT DETAILS */}
            <div className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm">
              {selectedProduct ? (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-[1.25rem] bg-slate-100">
                    <Package2 className="h-7 w-7 text-slate-700" />
                  </div>

                  <h2 className="mt-4 text-xl font-semibold tracking-tight">
                    {selectedProduct.name}
                  </h2>

                  <p className="mt-1.5 text-sm text-slate-500">
                    SKU • {selectedProduct.sku}
                  </p>

                  <div className="mt-4 space-y-3">
                    <div className="rounded-2xl bg-slate-50 p-3.5">
                      <p className="text-xs text-slate-500">Category</p>
                      <p className="mt-1 text-base font-semibold">{selectedProduct.category}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3.5">
                      <p className="text-xs text-slate-500">Inventory</p>
                      <p className="mt-1 text-base font-semibold">{selectedProduct.stock} units</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3.5">
                      <p className="text-xs text-slate-500">Price</p>
                      <p className="mt-1 text-base font-semibold">{selectedProduct.price}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3.5">
                      <p className="text-xs text-slate-500">Last updated</p>
                      <p className="mt-1 text-base font-semibold">{selectedProduct.updated}</p>
                    </div>
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
                      Edit
                    </button>
                    <button
                      onClick={() => deleteProduct(selectedProduct.id)}
                      className="flex-1 rounded-full bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 transition hover:bg-red-100"
                    >
                      Delete
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-slate-100">
                    <Package2 className="h-8 w-8 text-slate-400" />
                  </div>
                  <h2 className="mt-4 text-xl font-semibold text-slate-900">Product details</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Select a product to view inventory and SKU details.
                  </p>
                </div>
              )}
            </div>

            {/* QUICK STATS */}

          </aside>
        </section>
      </main>

      {/* ─── ADD PRODUCT MODAL ────────────────────────────────────────────────── */}
      <Dialog open={showAddModal} onOpenChange={(open) => {
        setShowAddModal(open);
        if (!open) { setForm(EMPTY_FORM); setAddSuccess(false); }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Package2 className="h-5 w-5 text-slate-700" />
              Add new product
            </DialogTitle>
            <DialogDescription>
              Creates a record in <span className="font-medium text-slate-700">products</span> and an initial entry in the <span className="font-medium text-slate-700">inventory</span> table.
              Product ID and Inventory ID are auto-generated.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddProduct} className="mt-2 space-y-5">

            {/* ── PRODUCTS TABLE SECTION ── */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                products table
              </p>
              <div className="grid gap-3 sm:grid-cols-2">

                {/* product_name */}
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    product_name <span className="text-red-500">*</span>
                  </label>
                  <Input
                    value={form.product_name}
                    onChange={(e) => handleFormChange('product_name', e.target.value)}
                    placeholder="e.g. iPhone 17 Pro Max"
                    required
                    className="rounded-xl"
                  />
                </div>

                {/* category */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    category <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <select
                      value={form.category}
                      onChange={(e) => handleFormChange('category', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                      required
                    >
                      {PRODUCT_CATEGORIES.map((cat) => (
                        <option key={cat}>{cat}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                {/* unit_price */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    unit_price (₹) <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.unit_price}
                    onChange={(e) => handleFormChange('unit_price', e.target.value)}
                    placeholder="e.g. 174900"
                    required
                    className="rounded-xl"
                  />
                </div>

                {/* supplier_name */}
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    supplier_name
                  </label>
                  <Input
                    value={form.supplier_name}
                    onChange={(e) => handleFormChange('supplier_name', e.target.value)}
                    placeholder="e.g. Apple Inc."
                    className="rounded-xl"
                  />
                </div>

              </div>
            </div>

            {/* ── INVENTORY TABLE SECTION ── */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                inventory table
              </p>
              <div className="grid gap-3 sm:grid-cols-3">

                {/* quantity */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    quantity <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={form.quantity}
                    onChange={(e) => handleFormChange('quantity', e.target.value)}
                    placeholder="e.g. 120"
                    required
                    className="rounded-xl"
                  />
                </div>

                {/* threshold_limit */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    threshold_limit <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={form.threshold_limit}
                    onChange={(e) => handleFormChange('threshold_limit', e.target.value)}
                    placeholder="e.g. 20"
                    required
                    className="rounded-xl"
                  />
                </div>

                {/* hub_id */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    hub_id
                  </label>
                  <Input
                    value={form.hub_id}
                    onChange={(e) => handleFormChange('hub_id', e.target.value)}
                    placeholder="e.g. W001"
                    className="rounded-xl"
                  />
                </div>

              </div>

              {/* Live status preview */}
              {(form.quantity !== '' && form.threshold_limit !== '') && (
                <div className="mt-3 flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5">
                  <span className="text-xs text-slate-500">Computed status:</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                    parseInt(form.quantity) === 0
                      ? 'bg-red-50 text-red-700'
                      : parseInt(form.quantity) <= parseInt(form.threshold_limit)
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-emerald-50 text-emerald-700'
                  }`}>
                    {parseInt(form.quantity) === 0
                      ? 'Out of Stock'
                      : parseInt(form.quantity) <= parseInt(form.threshold_limit)
                      ? 'Low Stock'
                      : 'Healthy'}
                  </span>
                  <span className="text-xs text-slate-400">(quantity vs threshold_limit)</span>
                </div>
              )}

              {/* Auto-generated IDs notice */}
              <div className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-400">
                <span className="font-medium text-slate-600">product_id</span> and <span className="font-medium text-slate-600">inventory_id</span> are auto-generated on save.
                <span className="ml-2 font-medium text-slate-600">last_updated</span> is set to now.
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-1">
              <Button
                type="button"
                variant="outline"
                className="rounded-full px-5"
                onClick={() => { setShowAddModal(false); setForm(EMPTY_FORM); }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={addSubmitting || addSuccess}
                className="rounded-full bg-slate-950 px-6 text-white min-w-[140px]"
              >
                {addSuccess ? (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-400" />
                    Added!
                  </>
                ) : addSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving…
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Add product
                  </>
                )}
              </Button>
            </div>

          </form>
        </DialogContent>
      </Dialog>

    </div>
  );
}
