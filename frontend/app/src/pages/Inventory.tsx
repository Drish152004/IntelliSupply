import { useEffect, useMemo, useState } from 'react';
import Navbar from '@/components/Navbar';
import AICopilot from '@/components/AICopilot';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
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
  ShieldCheck,
} from 'lucide-react';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

import {
  createInventoryStockEntry,
  deleteInventoryProduct,
  listInventoryCategories,
  listInventoryCities,
  listInventoryHubs,
  listInventoryProducts,
  listInventoryProductsByCategory,
  type InventoryCatalogProduct,
  type InventoryCityItem,
  type InventoryHubItem,
} from '@/lib/api';

const DEFAULT_CATEGORIES = [
  'Electronics',
  'Furniture',
  'Groceries',
  'Toys',
];

const statuses = [
  'All',
  'Healthy',
  'Low Stock',
  'Out of Stock',
];
const WEATHER_OPTIONS = [
  'Sunny',
  'Cloudy',
  'Rainy',
  'Snowy',
];

const SEASONALITY_OPTIONS = [
  'Spring',
  'Summer',
  'Autumn',
  'Winter',
];

const YES_NO_OPTIONS = [
  { label: 'No', value: '0' },
  { label: 'Yes', value: '1' },
];

const EMPTY_FORM = {
  category: '',
  product_id: '',
  city_id: '',
  hub_id: '',
  inventory_level: '',
  units_ordered: '',
  price: '',
  demand: '',
  discount: '',
  weather_condition: '',
  seasonality: '',
  promotion: '0',
  epidemic: '0',
};

type ProductRow = {
  id: string;
  name: string;
  sku: string;
  category: string;
  stock: number;
  price: string;
  status: string;
  updated: string;
};

export default function Inventory() {
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [availableCategories, setAvailableCategories] = useState<string[]>(DEFAULT_CATEGORIES);
  const [categoryProducts, setCategoryProducts] = useState<InventoryCatalogProduct[]>([]);
  const [cities, setCities] = useState<InventoryCityItem[]>([]);
  const [hubs, setHubs] = useState<InventoryHubItem[]>([]);
  const [dropdownLoading, setDropdownLoading] = useState(false);

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selectedProduct, setSelectedProduct] = useState<ProductRow | null>(null);

  const [showAddModal, setShowAddModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);

  const filterCategories = useMemo(
    () => ['All', ...availableCategories],
    [availableCategories],
  );

  const handleFormChange = (field: keyof typeof EMPTY_FORM, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const mapProductRow = (product: any): ProductRow => ({
    id: product.id,
    name: product.name,
    sku: product.id,
    category: product.category ?? 'General',
    stock: product.stock ?? 0,
    price: product.unit_price
      ? `₹${Number(product.unit_price).toLocaleString('en-IN')}`
      : '₹0',
    status: product.status ?? 'Healthy',
    updated: 'Synced',
  });

  const loadInventory = async () => {
    setLoading(true);

    try {
      const rows = await listInventoryProducts();

      setLoadError(null);
      setProducts(rows.map(mapProductRow));
    } catch {
      setLoadError('Unable to load inventory. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    async function loadDropdownData() {
      setDropdownLoading(true);

      try {
        const [categoryRows, cityRows] = await Promise.all([
          listInventoryCategories().catch(() => DEFAULT_CATEGORIES),
          listInventoryCities().catch(() => []),
        ]);

        const normalizedCategories = categoryRows.length
          ? categoryRows.slice(0, 4)
          : DEFAULT_CATEGORIES;

        setAvailableCategories(normalizedCategories);
        setCities(cityRows);
      } finally {
        setDropdownLoading(false);
      }
    }

    void loadInventory();
    void loadDropdownData();
  }, []);

  useEffect(() => {
    if (!form.category) {
      setCategoryProducts([]);
      return;
    }

    setForm((prev) => ({
      ...prev,
      product_id: '',
    }));

    void listInventoryProductsByCategory(form.category)
      .then(setCategoryProducts)
      .catch(() => setCategoryProducts([]));
  }, [form.category]);

  useEffect(() => {
    if (!form.city_id) {
      setHubs([]);
      return;
    }

    setForm((prev) => ({
      ...prev,
      hub_id: '',
    }));

    void listInventoryHubs(form.city_id)
      .then(setHubs)
      .catch(() => setHubs([]));
  }, [form.city_id]);

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddSubmitting(true);
    setAddSuccess(false);

    try {
      const created = await createInventoryStockEntry({
        category: form.category,
        product_id: form.product_id,
        city_id: Number(form.city_id),
        hub_id: Number(form.hub_id),
        inventory_level: Number(form.inventory_level || 0),
        units_ordered: form.units_ordered ? Number(form.units_ordered) : 0,
        price: form.price ? Number(form.price) : undefined,
        demand: form.demand ? Number(form.demand) : 0,
        discount: form.discount ? Number(form.discount) : 0,
        weather_condition: form.weather_condition || undefined,
        seasonality: form.seasonality || undefined,
        promotion: Number(form.promotion || 0),
        epidemic: Number(form.epidemic || 0),
      });

      const newProduct: ProductRow = {
        id: created.id,
        name: created.name,
        sku: created.id,
        category: created.category ?? form.category,
        stock: created.stock,
        price: created.unit_price
          ? `₹${Number(created.unit_price).toLocaleString('en-IN')}`
          : form.price
            ? `₹${Number(form.price).toLocaleString('en-IN')}`
            : '₹0',
        status: created.status,
        updated: 'Just now',
      };

      setProducts((prev) => [newProduct, ...prev]);
      setAddSuccess(true);

      setTimeout(() => {
        setShowAddModal(false);
        setAddSuccess(false);
        setForm(EMPTY_FORM);
        setCategoryProducts([]);
        setHubs([]);
      }, 1200);
    } catch (error) {
      console.error('Add inventory stock entry failed:', error);
      setLoadError('Unable to add inventory entry. Please check the form and try again.');
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
      // keep UI stable for now
    }

    if (selectedProduct?.id === id) {
      setSelectedProduct(null);
    }
  };

  const totalProducts = products.length;

  const lowStockCount = products.filter(
    (p) => p.status === 'Low Stock',
  ).length;

  const healthyCount = products.filter(
    (p) => p.status === 'Healthy',
  ).length;

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-950">
      <Navbar />

      <main className="max-w-[1750px] mx-auto px-6 lg:px-10 py-8">
        <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500 mb-2">
              Inventory workspace
            </p>

            <h1 className="text-3xl font-semibold tracking-tight">
              Inventory
            </h1>

            <p className="mt-2 text-sm text-slate-500 max-w-3xl leading-6">
              Manage product inventory and stock visibility from one centralized workspace.
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
                  {healthyCount}
                </h2>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-[1.25rem] bg-emerald-50">
                <TrendingUp className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </div>
        </section>

        {loadError && (
          <p className="mb-4 text-sm text-red-600">{loadError}</p>
        )}

        <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
          <div className="rounded-[2rem] border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-200 p-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div className="relative w-full xl:max-w-sm">
                  <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search products or SKU"
                    className="h-10 w-full rounded-full border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm outline-none transition focus:border-slate-400"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <div className="relative">
                    <select
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                      className="h-10 appearance-none rounded-full border border-slate-200 bg-white px-4 pr-9 text-sm font-medium outline-none"
                    >
                      {filterCategories.map((category) => (
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

            <div className="overflow-x-auto">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-16">
                  <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                  <p className="mt-4 text-sm text-slate-500">Loading inventory…</p>
                </div>
              ) : (
                <>
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
                                className={`h-full rounded-full ${product.status === 'Out of Stock'
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
                              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${product.status === 'Healthy'
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
                                  void deleteProduct(product.id);
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
                </>
              )}
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold text-slate-950">Inventory Copilot</p>
                  <p className="text-xs text-slate-500">Launch the AI assistant without taking over the page.</p>
                </div>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="w-full rounded-3xl bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900 border border-sky-100 hover:bg-sky-100">
                    Open Inventory Copilot
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[90vw] sm:max-w-[980px] p-0">
                  <DialogHeader className="bg-slate-950/5 px-6 py-5">
                    <DialogTitle>Inventory Copilot</DialogTitle>
                    <DialogDescription>Ask about reorder planning, shortage risk, and inbound stock using AI.</DialogDescription>
                  </DialogHeader>
                  <div className="h-[640px]">
                    <AICopilot domain="inventory" />
                  </div>
                </DialogContent>
              </Dialog>
            </div>

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
                      onClick={() => void deleteProduct(selectedProduct.id)}
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
          </aside>
        </section>
      </main>

      <Dialog
        open={showAddModal}
        onOpenChange={(open) => {
          setShowAddModal(open);
          if (!open) {
            setForm(EMPTY_FORM);
            setAddSuccess(false);
            setCategoryProducts([]);
            setHubs([]);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Package2 className="h-5 w-5 text-slate-700" />
              Add inventory stock
            </DialogTitle>
            <DialogDescription>
              Select a category, product, city, and hub, then create a new stock entry in the planning dataset.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddProduct} className="mt-2 space-y-5">
            {/* Select product */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Select product
              </p>

              <div className="grid gap-3 sm:grid-cols-2">
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
                      <option value="">Select category</option>
                      {availableCategories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    product <span className="text-red-500">*</span>
                  </label>

                  <div className="relative">
                    <select
                      value={form.product_id}
                      onChange={(e) => handleFormChange('product_id', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                      required
                      disabled={!form.category}
                    >
                      <option value="">
                        {form.category ? 'Select product' : 'Select category first'}
                      </option>

                      {categoryProducts.map((product) => (
                        <option
                          key={`${product.product_id}-${product.category}`}
                          value={product.product_id}
                        >
                          {product.product_display_name || product.product_name || product.product_id}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>
              </div>
            </div>

            {/* Select location */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Select location
              </p>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    city <span className="text-red-500">*</span>
                  </label>

                  <div className="relative">
                    <select
                      value={form.city_id}
                      onChange={(e) => handleFormChange('city_id', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                      required
                    >
                      <option value="">Select city</option>
                      {cities.map((city) => (
                        <option key={city.city_id} value={city.city_id}>
                          {city.city_name}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    hub <span className="text-red-500">*</span>
                  </label>

                  <div className="relative">
                    <select
                      value={form.hub_id}
                      onChange={(e) => handleFormChange('hub_id', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                      required
                      disabled={!form.city_id}
                    >
                      <option value="">
                        {form.city_id ? 'Select hub' : 'Select city first'}
                      </option>

                      {hubs.map((hub) => (
                        <option key={hub.hub_id} value={hub.hub_id}>
                          {hub.hub_name || `Hub ${hub.hub_id}`}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>
              </div>
            </div>

            {/* Stock details */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Stock details
              </p>

              <div className="grid gap-3 sm:grid-cols-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    inventory_level <span className="text-red-500">*</span>
                  </label>

                  <Input
                    type="number"
                    min="0"
                    value={form.inventory_level}
                    onChange={(e) => handleFormChange('inventory_level', e.target.value)}
                    placeholder="e.g. 120"
                    required
                    className="rounded-xl"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    units_ordered
                  </label>

                  <Input
                    type="number"
                    min="0"
                    value={form.units_ordered}
                    onChange={(e) => handleFormChange('units_ordered', e.target.value)}
                    placeholder="e.g. 50"
                    className="rounded-xl"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    price ₹
                  </label>

                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.price}
                    onChange={(e) => handleFormChange('price', e.target.value)}
                    placeholder="e.g. 174900"
                    className="rounded-xl"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    discount
                  </label>

                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.discount}
                    onChange={(e) => handleFormChange('discount', e.target.value)}
                    placeholder="e.g. 5"
                    className="rounded-xl"
                  />
                </div>
              </div>
            </div>

            {/* Context details */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Context details
              </p>

              <div className="grid gap-3 sm:grid-cols-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    weather_condition
                  </label>

                  <div className="relative">
                    <select
                      value={form.weather_condition}
                      onChange={(e) => handleFormChange('weather_condition', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                    >
                      <option value="">Select weather</option>
                      {WEATHER_OPTIONS.map((weather) => (
                        <option key={weather} value={weather}>
                          {weather}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    seasonality
                  </label>

                  <div className="relative">
                    <select
                      value={form.seasonality}
                      onChange={(e) => handleFormChange('seasonality', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                    >
                      <option value="">Select season</option>
                      {SEASONALITY_OPTIONS.map((season) => (
                        <option key={season} value={season}>
                          {season}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    promotion
                  </label>

                  <div className="relative">
                    <select
                      value={form.promotion}
                      onChange={(e) => handleFormChange('promotion', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                    >
                      {YES_NO_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700">
                    epidemic
                  </label>

                  <div className="relative">
                    <select
                      value={form.epidemic}
                      onChange={(e) => handleFormChange('epidemic', e.target.value)}
                      className="h-10 w-full appearance-none rounded-xl border border-input bg-background px-3 pr-8 text-sm outline-none focus:border-slate-400"
                    >
                      {YES_NO_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>

                    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  </div>
                </div>
              </div>

              <div className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-400">
                <span className="font-medium text-slate-600">date</span> is set by the backend.
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-1">
              <Button
                type="button"
                variant="outline"
                className="rounded-full px-5"
                onClick={() => {
                  setShowAddModal(false);
                  setForm(EMPTY_FORM);
                  setCategoryProducts([]);
                  setHubs([]);
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  addSubmitting ||
                  addSuccess ||
                  dropdownLoading ||
                  !form.category ||
                  !form.product_id ||
                  !form.city_id ||
                  !form.hub_id ||
                  !form.inventory_level
                }
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
                    Add stock
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