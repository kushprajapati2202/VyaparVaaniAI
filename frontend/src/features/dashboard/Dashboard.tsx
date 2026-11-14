import React from 'react';
import { 
  TrendingUp, ShoppingBag, CreditCard, AlertCircle, Clock, Zap, 
  ChevronRight, ArrowUpRight, Plus, PackageCheck, Truck
} from 'lucide-react';
import { DailyMetrics, Order, Product } from '../../types';

interface DashboardProps {
  metrics: DailyMetrics | null;
  orders: Order[];
  inventory: Product[];
  onNavigateTab: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ metrics, orders, inventory, onNavigateTab }) => {
  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden bg-gradient-to-r from-surface via-card to-surface p-6 sm:p-8 rounded-3xl border border-border shadow-card">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Live Store Counter</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-display font-extrabold text-white tracking-tight">
              Shree Ganesh Kirana & General Store
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-xl">
              Voice-driven operations active • 95.8% transactions automated without manual typing
            </p>
          </div>

          <button
            onClick={() => onNavigateTab('voice')}
            className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-gradient-to-r from-saffron-500 to-amber-500 hover:from-saffron-600 hover:to-amber-600 text-slate-950 font-bold text-xs sm:text-sm shadow-glow-saffron transition-all hover:scale-105 active:scale-95"
          >
            <Zap className="w-4 h-4 fill-current" />
            <span>Launch Voice Counter (બોલો)</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Metric 1: Today's Revenue */}
        <div className="bg-surface border border-border hover:border-border-strong rounded-2xl p-5 shadow-sm transition-all group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Today's Total Sales</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-display font-extrabold text-white tracking-tight">
            ₹{metrics ? metrics.total_sales_today.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
          </div>
          <p className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1 font-medium">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>+18.4%</span> vs yesterday's manual counter
          </p>
        </div>

        {/* Metric 2: Orders Count */}
        <div className="bg-surface border border-border hover:border-border-strong rounded-2xl p-5 shadow-sm transition-all group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Voice Orders Processed</span>
            <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-display font-extrabold text-white tracking-tight">
            {metrics ? metrics.orders_count_today : 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Automated via Gujarati & Hindi Voice
          </p>
        </div>

        {/* Metric 3: Khata Credit */}
        <div className="bg-surface border border-border hover:border-border-strong rounded-2xl p-5 shadow-sm transition-all group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Outstanding Khata Balance</span>
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 group-hover:scale-110 transition-transform">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-display font-extrabold text-white tracking-tight">
            ₹{metrics ? metrics.total_outstanding_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
          </div>
          <p className="text-[11px] text-amber-400 mt-2 font-medium">
            Across 5 active verified merchants
          </p>
        </div>

        {/* Metric 4: Efficiency */}
        <div className="bg-surface border border-border hover:border-border-strong rounded-2xl p-5 shadow-sm transition-all group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Automation & Time Saved</span>
            <div className="w-8 h-8 rounded-xl bg-saffron-500/10 flex items-center justify-center text-saffron-400 group-hover:scale-110 transition-transform">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-display font-extrabold text-white tracking-tight">
            {metrics ? metrics.automation_rate_percent : 95.8}%
          </div>
          <p className="text-[11px] text-saffron-400 mt-2 font-medium">
            ~{metrics ? metrics.time_saved_hours : 4.8} hours saved today
          </p>
        </div>

      </div>

      {/* Two Column Section: Live Counter Orders + Inventory Watchlist */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Recent Orders (7 cols) */}
        <div className="lg:col-span-7 bg-surface border border-border rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-bold text-white">Live Counter Orders</h2>
              <p className="text-[11px] text-slate-400">Created through spoken instructions & confirmed</p>
            </div>
            <button
              onClick={() => onNavigateTab('orders')}
              className="text-xs text-saffron-400 hover:text-saffron-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-border/60">
            {orders.slice(0, 5).map((ord) => (
              <div key={ord.id} className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white">{ord.order_number}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      ord.status === 'CONFIRMED'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : ord.status === 'PENDING_APPROVAL'
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {ord.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {ord.customer_name} • <span className="text-slate-300">{ord.payment_method}</span>
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold font-mono text-white">₹{ord.total_amount.toFixed(2)}</div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(ord.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {orders.length === 0 && (
              <p className="text-xs text-slate-500 py-6 text-center">No orders recorded yet. Speak a voice order!</p>
            )}
          </div>
        </div>

        {/* Inventory Watchlist (5 cols) */}
        <div className="lg:col-span-5 bg-surface border border-border rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-bold text-white">Stock Level Monitor</h2>
              <p className="text-[11px] text-slate-400">Low stock automated alerts</p>
            </div>
            <button
              onClick={() => onNavigateTab('inventory')}
              className="text-xs text-saffron-400 hover:text-saffron-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>Manage</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {inventory.slice(0, 5).map((prod) => {
              const pct = Math.min(100, Math.round((prod.current_stock / (prod.min_stock_alert * 3)) * 100));
              return (
                <div key={prod.id} className="p-3.5 rounded-2xl bg-card border border-border/80">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="font-semibold text-slate-200">{prod.name}</span>
                    <span className={`font-mono font-bold ${prod.is_low_stock ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {prod.current_stock} {prod.unit}
                    </span>
                  </div>
                  <div className="w-full bg-background h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        prod.is_low_stock ? 'bg-amber-400' : 'bg-primary'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

    </div>
  );
};
