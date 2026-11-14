import React from 'react';
import { Package, AlertCircle, Sparkles } from 'lucide-react';
import { Product } from '../../types';

interface InventoryPageProps {
  inventory: Product[];
}

export const InventoryPage: React.FC<InventoryPageProps> = ({ inventory }) => {
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
            Real-time stock deduction, vernacular matching (ચોખા, ખાંડ, તેલ), and automated replenishment alerts.
          </p>
        </div>
        <span className="text-xs font-mono px-3.5 py-1.5 bg-card border border-border rounded-xl text-slate-300">
          Catalogue SKUs: <strong className="text-white">{inventory.length}</strong>
        </span>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {inventory.map((prod) => (
          <div key={prod.id} className="bg-surface border border-border rounded-3xl p-5 shadow-sm space-y-4 hover:border-border-strong transition-all">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-background text-slate-400 border border-border">
                  {prod.sku}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">{prod.name}</h3>
                <p className="text-xs text-slate-400">{prod.category}</p>
              </div>
              {prod.is_low_stock && (
                <span className="flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-full font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  <AlertCircle className="w-3 h-3" />
                  <span>Low Stock</span>
                </span>
              )}
            </div>

            <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Selling Price</span>
                <span className="font-bold text-white text-sm">₹{prod.selling_price.toFixed(2)} / {prod.unit}</span>
              </div>
              <div className="text-right">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">In Stock</span>
                <span className={`font-mono font-bold text-sm ${prod.is_low_stock ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {prod.current_stock} {prod.unit}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};
