import React from 'react';
import { 
  TrendingUp, ShoppingBag, CreditCard, AlertCircle, Clock, Zap, CheckCircle2, ChevronRight 
} from 'lucide-react';
import { DailyMetrics, Order, Product } from '../../types';

interface DashboardProps {
  metrics: DailyMetrics | null;
  orders: Order[];
  inventory: Product[];
  onNavigateTab: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ metrics, orders, inventory, onNavigateTab }) => {
  const lowStockItems = inventory.filter((i) => i.is_low_stock);

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gradient-to-r from-card to-surface p-6 rounded-2xl border border-border">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Shree Ganesh Kirana & General Store</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time MSME Store Intelligence • Automated via Gemini Voice Agent
          </p>
        </div>
        <button
          onClick={() => onNavigateTab('voice')}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-slate-950 font-bold text-xs hover:bg-primary-hover shadow-lg shadow-cyan-500/20 transition-all"
        >
          <Zap className="w-4 h-4 fill-current" />
          <span>Launch Voice Command</span>
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Metric 1 */}
        <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Today's Sales</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            ₹{metrics ? metrics.total_sales_today.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
          </div>
          <p className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1">
            <span>+18.4%</span> vs yesterday's counter sales
          </p>
        </div>

        {/* Metric 2 */}
        <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Orders Recorded</span>
            <ShoppingBag className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {metrics ? metrics.orders_count_today : 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Automated via Gujarati & Hindi Voice
          </p>
        </div>

        {/* Metric 3 */}
        <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Outstanding Khata Credit</span>
            <CreditCard className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            ₹{metrics ? metrics.total_outstanding_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '0.00'}
          </div>
          <p className="text-[11px] text-amber-400 mt-2">
            Managed across 5 active retailers
          </p>
        </div>

        {/* Metric 4 */}
        <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Automation & Efficiency</span>
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {metrics ? metrics.automation_rate_percent : 95.8}%
          </div>
          <p className="text-[11px] text-primary mt-2">
            ~{metrics ? metrics.time_saved_hours : 4.8} hrs saved today
          </p>
        </div>

      </div>

      {/* Two Column Layout: Recent Orders & Stock Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Recent Orders (7 cols) */}
        <div className="lg:col-span-7 bg-surface border border-border rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white">Recent Counter Orders</h2>
            <button
              onClick={() => onNavigateTab('orders')}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-border/60">
            {orders.slice(0, 5).map((ord) => (
              <div key={ord.id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200">{ord.order_number}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      ord.status === 'CONFIRMED'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : ord.status === 'PENDING_APPROVAL'
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {ord.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{ord.customer_name} • {ord.payment_method}</p>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-white">₹{ord.total_amount.toFixed(2)}</div>
                  <span className="text-[10px] text-slate-500">
                    {new Date(ord.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {orders.length === 0 && (
              <p className="text-xs text-slate-500 py-4 text-center">No orders recorded yet today.</p>
            )}
          </div>
        </div>

        {/* Low Stock Alerts (5 cols) */}
        <div className="lg:col-span-5 bg-surface border border-border rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-bold text-white">Inventory Stock Status</h2>
            </div>
            <button
              onClick={() => onNavigateTab('inventory')}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              <span>Manage</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {inventory.slice(0, 5).map((prod) => {
              const pct = Math.min(100, Math.round((prod.current_stock / (prod.min_stock_alert * 3)) * 100));
              return (
                <div key={prod.id} className="p-3 rounded-xl bg-card border border-border">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-semibold text-slate-200">{prod.name}</span>
                    <span className={`font-mono text-xs ${prod.is_low_stock ? 'text-amber-400 font-bold' : 'text-slate-300'}`}>
                      {prod.current_stock} {prod.unit}
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
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
