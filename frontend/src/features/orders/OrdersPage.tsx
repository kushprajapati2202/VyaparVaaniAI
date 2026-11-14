import React from 'react';
import { ShoppingBag, Truck, Calendar, ArrowUpRight } from 'lucide-react';
import { Order } from '../../types';

interface OrdersPageProps {
  orders: Order[];
}

export const OrdersPage: React.FC<OrdersPageProps> = ({ orders }) => {
  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-saffron-400" />
            <span>Store Orders Ledger</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Complete audit trail of all voice-created, counter and dispatch orders.
          </p>
        </div>
        <span className="text-xs font-mono px-3.5 py-1.5 bg-card border border-border rounded-xl text-slate-300">
          Total Orders: <strong className="text-white">{orders.length}</strong>
        </span>
      </div>

      {/* Orders Table Card */}
      <div className="bg-surface border border-border rounded-3xl overflow-hidden shadow-card">
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
                <th className="px-6 py-4">Created Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-slate-200">
              {orders.map((ord) => (
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
              {orders.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    No orders recorded yet. Speak a voice order to test the pipeline!
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
