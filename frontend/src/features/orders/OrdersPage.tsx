import React, { useState } from 'react';
import { ShoppingBag, Truck, Calendar, Search, Filter, CheckCircle2, Clock, ShieldAlert } from 'lucide-react';
import { Order } from '../../types';

interface OrdersPageProps {
  orders: Order[];
}

export const OrdersPage: React.FC<OrdersPageProps> = ({ orders }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filteredOrders = orders.filter((ord) => {
    const matchesSearch = 
      ord.order_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ord.customer_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || ord.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-saffron-400" />
            <span>Store Orders Ledger</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-step orders created through vernacular voice instructions.
          </p>
        </div>
        
        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          <span className="text-xs font-mono px-3.5 py-1.5 bg-card border border-border rounded-xl text-slate-300">
            Orders: <strong className="text-white">{filteredOrders.length}</strong> / {orders.length}
          </span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-surface border border-border rounded-2xl p-3 sm:p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
        
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search order ref or customer..."
            className="w-full bg-background border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-saffron-500 transition-colors"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'CONFIRMED', 'PENDING_APPROVAL'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                statusFilter === st
                  ? 'bg-saffron-500 text-slate-950 font-bold shadow-sm'
                  : 'bg-card text-slate-400 hover:text-white border border-border'
              }`}
            >
              {st === 'ALL' ? 'All Orders' : st === 'CONFIRMED' ? 'Confirmed' : 'Pending Approval'}
            </button>
          ))}
        </div>

      </div>

      {/* Mobile Card View (< md) */}
      <div className="md:hidden space-y-3">
        {filteredOrders.map((ord) => (
          <div key={ord.id} className="bg-surface border border-border rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-mono text-xs font-bold text-saffron-400">{ord.order_number}</span>
                <h3 className="font-bold text-white text-sm">{ord.customer_name}</h3>
              </div>
              <div className="text-right">
                <span className="text-base font-extrabold font-mono text-white">₹{ord.total_amount.toFixed(2)}</span>
                <span className="block text-[10px] text-slate-500 font-mono">
                  {new Date(ord.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-card border border-border/80 text-xs text-slate-300">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Items</span>
              <p className="line-clamp-2 mt-0.5">
                {ord.items && ord.items.length > 0 ? (
                  ord.items.map((it) => `${it.quantity} ${it.unit} ${it.product_name}`).join(', ')
                ) : (
                  'Counter Sale'
                )}
              </p>
            </div>

            <div className="flex items-center justify-between pt-1 text-xs">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-background text-[10px] font-mono text-slate-300 border border-border">
                  {ord.payment_method}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-slate-400">
                  <Truck className="w-3.5 h-3.5 text-primary" />
                  <span>{ord.delivery_status || 'Scheduled'}</span>
                </span>
              </div>

              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                ord.status === 'CONFIRMED'
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : ord.status === 'PENDING_APPROVAL'
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  : 'bg-slate-800 text-slate-300'
              }`}>
                {ord.status}
              </span>
            </div>
          </div>
        ))}
        {filteredOrders.length === 0 && (
          <div className="bg-surface border border-border rounded-2xl p-8 text-center text-slate-500 text-xs">
            No matching orders found.
          </div>
        )}
      </div>

      {/* Desktop Table View (>= md) */}
      <div className="hidden md:block bg-surface border border-border rounded-3xl overflow-hidden shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-card border-b border-border text-slate-400 uppercase font-mono text-[10px] tracking-wider">
              <tr>
                <th className="px-6 py-4">Order Ref</th>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">Line Items</th>
                <th className="px-6 py-4">Payment</th>
                <th className="px-6 py-4">Total (₹)</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Delivery</th>
                <th className="px-6 py-4">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-slate-200">
              {filteredOrders.map((ord) => (
                <tr key={ord.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-saffron-400">{ord.order_number}</td>
                  <td className="px-6 py-4 font-bold text-white">{ord.customer_name}</td>
                  <td className="px-6 py-4 text-slate-400 max-w-xs truncate">
                    {ord.items && ord.items.length > 0 ? (
                      ord.items.map((it) => `${it.quantity} ${it.unit} ${it.product_name}`).join(', ')
                    ) : (
                      'Multi-item order'
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-lg bg-background text-[10px] font-mono text-slate-300 border border-border">
                      {ord.payment_method}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono font-bold text-white text-sm">
                    ₹{ord.total_amount.toFixed(2)}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                      ord.status === 'CONFIRMED'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : ord.status === 'PENDING_APPROVAL'
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {ord.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="flex items-center gap-1.5 text-[11px] text-slate-300">
                      <Truck className="w-3.5 h-3.5 text-primary" />
                      <span>{ord.delivery_status || 'Scheduled'}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-400 font-mono text-[11px]">
                    {new Date(ord.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
              {filteredOrders.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    No orders match your filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
