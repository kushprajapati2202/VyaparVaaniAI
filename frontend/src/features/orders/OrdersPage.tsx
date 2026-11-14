import React from 'react';
import { ShoppingCart, CheckCircle, Clock, AlertTriangle, Truck } from 'lucide-react';
import { Order } from '../../types';

interface OrdersPageProps {
  orders: Order[];
}

export const OrdersPage: React.FC<OrdersPageProps> = ({ orders }) => {
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-primary" />
            <span>Orders Ledger</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Complete lifecycle of all voice-created and counter transactions.
          </p>
        </div>
        <span className="text-xs font-mono px-3 py-1 bg-card border border-border rounded-xl text-slate-300">
          Total Orders: {orders.length}
        </span>
      </div>

      {/* Orders Table */}
      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-card/70 border-b border-border text-slate-400 uppercase font-mono text-[10px]">
              <tr>
                <th className="px-5 py-3.5">Order Ref</th>
                <th className="px-5 py-3.5">Customer</th>
                <th className="px-5 py-3.5">Items</th>
                <th className="px-5 py-3.5">Payment</th>
                <th className="px-5 py-3.5">Total (₹)</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Delivery</th>
                <th className="px-5 py-3.5">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-slate-200">
              {orders.map((ord) => (
                <tr key={ord.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-5 py-3.5 font-mono font-bold text-primary">{ord.order_number}</td>
                  <td className="px-5 py-3.5 font-medium text-white">{ord.customer_name}</td>
                  <td className="px-5 py-3.5 text-slate-400">
                    {ord.items && ord.items.length > 0 ? (
                      ord.items.map((it) => `${it.quantity} ${it.unit} ${it.product_name}`).join(', ')
                    ) : (
                      'Multi-item'
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-300">
                      {ord.payment_method}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-bold text-white">₹{ord.total_amount.toFixed(2)}</td>
                  <td className="px-5 py-3.5">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      ord.status === 'CONFIRMED'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : ord.status === 'PENDING_APPROVAL'
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {ord.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="flex items-center gap-1 text-[11px] text-slate-400">
                      <Truck className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{ord.delivery_status || 'Scheduled'}</span>
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-slate-400 font-mono text-[11px]">
                    {new Date(ord.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
              {orders.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">
                    No orders recorded yet. Speak a voice order to get started!
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
