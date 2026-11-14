import React, { useState } from 'react';
import { Package, AlertCircle, Search, Filter, Layers, Check } from 'lucide-react';
import { Product } from '../../types';

interface InventoryPageProps {
  inventory: Product[];
}

export const InventoryPage: React.FC<InventoryPageProps> = ({ inventory }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [lowStockOnly, setLowStockOnly] = useState(false);

  const categories = ['ALL', ...Array.from(new Set(inventory.map((i) => i.category)))];

  const filteredItems = inventory.filter((prod) => {
    const matchesSearch = 
      prod.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prod.sku.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prod.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCat = selectedCategory === 'ALL' || prod.category === selectedCategory;
    const matchesStock = !lowStockOnly || prod.is_low_stock;
    return matchesSearch && matchesCat && matchesStock;
  });

  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Package className="w-5 h-5 text-saffron-400" />
            <span>Store Inventory & Catalogue</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time stock deduction, vernacular matching (ચોખા, ખાંડ, તેલ), and automated low-stock alerts.
          </p>
        </div>
        
        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          <span className="text-xs font-mono px-3.5 py-1.5 bg-card border border-border rounded-xl text-slate-300">
            SKUs: <strong className="text-white">{filteredItems.length}</strong> / {inventory.length}
          </span>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="bg-surface border border-border rounded-2xl p-4 space-y-3 shadow-sm">
        
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          
          {/* Search Box */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search product (Rice, Wheat, Oil)..."
              className="w-full bg-background border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-saffron-500 transition-colors"
            />
          </div>

          {/* Low Stock Toggle Button */}
          <button
            onClick={() => setLowStockOnly(!lowStockOnly)}
            className={`w-full sm:w-auto flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
              lowStockOnly
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                : 'bg-card text-slate-400 border-border hover:text-white'
            }`}
          >
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>Low Stock Alerts Only</span>
          </button>
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                selectedCategory === cat
                  ? 'bg-saffron-500 text-slate-950 font-bold shadow-sm'
                  : 'bg-card text-slate-400 hover:text-white border border-border'
              }`}
            >
              {cat === 'ALL' ? 'All Categories' : cat}
            </button>
          ))}
        </div>

      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredItems.map((prod) => {
          const maxCapacity = Math.max(100, prod.min_stock_alert * 3);
          const stockPercent = Math.min(100, Math.round((prod.current_stock / maxCapacity) * 100));

          return (
            <div 
              key={prod.id} 
              className={`bg-surface border rounded-3xl p-5 shadow-sm space-y-4 transition-all hover:border-border-strong ${
                prod.is_low_stock ? 'border-amber-500/40 bg-amber-950/10' : 'border-border'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-background text-slate-400 border border-border">
                    {prod.sku}
                  </span>
                  <h3 className="text-base font-bold text-white mt-1.5">{prod.name}</h3>
                  <p className="text-xs text-slate-400">{prod.category}</p>
                </div>
                {prod.is_low_stock && (
                  <span className="flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-full font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 shrink-0">
                    <AlertCircle className="w-3 h-3" />
                    <span>Low Stock</span>
                  </span>
                )}
              </div>

              {/* Stock Bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px]">Stock Level ({stockPercent}%)</span>
                  <span className="text-slate-400 text-[11px]">Alert at &lt; {prod.min_stock_alert} {prod.unit}</span>
                </div>
                <div className="w-full bg-background h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      prod.is_low_stock ? 'bg-amber-400' : 'bg-primary'
                    }`}
                    style={{ width: `${stockPercent}%` }}
                  />
                </div>
              </div>

              {/* Price & Stock Stats */}
              <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Selling Price</span>
                  <span className="font-bold text-white text-sm">₹{prod.selling_price.toFixed(2)} / {prod.unit}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Available</span>
                  <span className={`font-mono font-bold text-sm ${prod.is_low_stock ? 'text-amber-400 font-extrabold' : 'text-emerald-400'}`}>
                    {prod.current_stock} {prod.unit}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredItems.length === 0 && (
        <div className="bg-surface border border-border rounded-3xl p-10 text-center text-slate-500 text-xs">
          No inventory products match your query.
        </div>
      )}

    </div>
  );
};
