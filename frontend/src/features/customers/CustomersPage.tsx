import React from 'react';
import { Users, Phone, MapPin, CreditCard, AlertTriangle } from 'lucide-react';
import { Customer } from '../../types';

interface CustomersPageProps {
  customers: Customer[];
}

export const CustomersPage: React.FC<CustomersPageProps> = ({ customers }) => {
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            <span>Customers & Khata Ledger</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Vernacular customer search, credit limit governance, and automated balance updates.
          </p>
        </div>
        <span className="text-xs font-mono px-3 py-1 bg-card border border-border rounded-xl text-slate-300">
          Active Merchants: {customers.length}
        </span>
      </div>

      {/* Customers List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {customers.map((cust) => {
          const utilization = (cust.outstanding_balance / cust.credit_limit) * 100;
          const isHighRisk = utilization >= 75;

          return (
            <div key={cust.id} className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="text-sm font-bold text-white">{cust.name}</h3>
                <div className="mt-1 space-y-1 text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-primary" />
                    <span>{cust.phone}</span>
                  </div>
                  {cust.address && (
                    <div className="flex items-center gap-1.5 text-[11px] line-clamp-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span>{cust.address}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Credit Status */}
              <div className="p-3 rounded-xl bg-card border border-border space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Outstanding Balance:</span>
                  <span className="font-bold text-white">₹{cust.outstanding_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Credit Limit:</span>
                  <span className="font-medium text-slate-300">₹{cust.credit_limit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>

                {/* Utilization Progress Bar */}
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span>Credit Utilization</span>
                    <span className={isHighRisk ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                      {utilization.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        isHighRisk ? 'bg-amber-400' : 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(100, utilization)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
