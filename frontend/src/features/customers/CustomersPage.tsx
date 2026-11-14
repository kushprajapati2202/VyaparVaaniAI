import React, { useState } from 'react';
import { Users, Phone, MapPin, CreditCard, Plus, CheckCircle2, Search, X } from 'lucide-react';
import { Customer } from '../../types';
import { api } from '../../services/api';

interface CustomersPageProps {
  customers: Customer[];
}

export const CustomersPage: React.FC<CustomersPageProps> = ({ customers }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [paymentModalCustomer, setPaymentModalCustomer] = useState<Customer | null>(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMode, setPaymentMode] = useState('CASH');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const filteredCustomers = customers.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.phone.includes(searchQuery)
  );

  const handleRecordPayment = async () => {
    if (!paymentModalCustomer || !paymentAmount) return;
    setIsSubmitting(true);
    try {
      await api.recordPayment(paymentModalCustomer.id, parseFloat(paymentAmount), paymentMode);
      setSuccessMessage(`₹${paymentAmount} payment recorded for ${paymentModalCustomer.name}!`);
      setTimeout(() => {
        setPaymentModalCustomer(null);
        setPaymentAmount('');
        setSuccessMessage('');
        window.location.reload();
      }, 1200);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-saffron-400" />
            <span>Customers & Khata Ledger</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Phonetic name matching (રાહુલ, અમિત, મહેશ), credit limit policies, and instant payment recording.
          </p>
        </div>
        
        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          <span className="text-xs font-mono px-3.5 py-1.5 bg-card border border-border rounded-xl text-slate-300">
            Active Accounts: <strong className="text-white">{filteredCustomers.length}</strong> / {customers.length}
          </span>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="bg-surface border border-border rounded-2xl p-4 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search customer by name or phone..."
            className="w-full bg-background border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-saffron-500 transition-colors"
          />
        </div>
      </div>

      {/* Customers List */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCustomers.map((cust) => {
          const utilization = (cust.outstanding_balance / cust.credit_limit) * 100;
          const isHighRisk = utilization >= 75;

          return (
            <div key={cust.id} className="bg-surface border border-border rounded-3xl p-5 shadow-sm space-y-4 hover:border-border-strong transition-all flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-bold text-white">{cust.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                    isHighRisk 
                      ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' 
                      : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  }`}>
                    {isHighRisk ? 'High Risk' : 'Good Standing'}
                  </span>
                </div>

                <div className="mt-2 space-y-1 text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-saffron-400 shrink-0" />
                    <span>{cust.phone}</span>
                  </div>
                  {cust.address && (
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500 line-clamp-1">
                      <MapPin className="w-3.5 h-3.5 shrink-0" />
                      <span>{cust.address}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Credit Status Card */}
              <div className="p-3.5 rounded-2xl bg-card border border-border space-y-2.5 my-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Outstanding Balance:</span>
                  <span className="font-mono font-bold text-white text-sm">
                    ₹{cust.outstanding_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Credit Limit:</span>
                  <span className="font-mono font-medium text-slate-300">
                    ₹{cust.credit_limit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Utilization Progress Bar */}
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span>Credit Utilization</span>
                    <span className={isHighRisk ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                      {utilization.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-background h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        isHighRisk ? 'bg-amber-400' : 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(100, utilization)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Quick Action Button: Record Payment */}
              <button
                onClick={() => setPaymentModalCustomer(cust)}
                className="w-full py-2.5 rounded-xl bg-card hover:bg-white/[0.06] text-saffron-400 font-bold text-xs border border-saffron-500/30 flex items-center justify-center gap-1.5 transition-all active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Record Payment (જમા કરો)</span>
              </button>
            </div>
          );
        })}
      </div>

      {/* Record Payment Dialog Modal */}
      {paymentModalCustomer && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4 relative">
            <button
              onClick={() => setPaymentModalCustomer(null)}
              className="absolute right-4 top-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div>
              <span className="text-[10px] font-bold text-saffron-400 uppercase tracking-wider">Khata Payment</span>
              <h2 className="text-lg font-bold text-white mt-0.5">Receive Payment from {paymentModalCustomer.name}</h2>
              <p className="text-xs text-slate-400">
                Current outstanding balance: <strong className="text-white">₹{paymentModalCustomer.outstanding_balance.toFixed(2)}</strong>
              </p>
            </div>

            {successMessage ? (
              <div className="p-4 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <span className="font-semibold">{successMessage}</span>
              </div>
            ) : (
              <div className="space-y-3 pt-2">
                <div>
                  <label className="text-xs text-slate-300 block mb-1">Payment Amount (₹)</label>
                  <input
                    type="number"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    placeholder="Enter amount (e.g. 2000)"
                    className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-saffron-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-300 block mb-1">Payment Mode</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['CASH', 'UPI'].map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setPaymentMode(m)}
                        className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                          paymentMode === m
                            ? 'bg-saffron-500 text-slate-950 border-saffron-500 font-extrabold'
                            : 'bg-card text-slate-300 border-border'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-2">
                  <button
                    disabled={isSubmitting || !paymentAmount}
                    onClick={handleRecordPayment}
                    className="flex-1 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 shadow-glow-emerald transition-all"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isSubmitting ? 'Recording...' : 'Confirm Receipt (જમા)'}</span>
                  </button>
                  <button
                    onClick={() => setPaymentModalCustomer(null)}
                    className="px-4 py-3 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold border border-border"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
