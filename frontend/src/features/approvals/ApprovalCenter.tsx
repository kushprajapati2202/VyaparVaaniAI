import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, User, Calendar, FileText, Check } from 'lucide-react';
import { Approval } from '../../types';
import { api } from '../../services/api';

interface ApprovalCenterProps {
  approvals: Approval[];
  onRefresh: () => void;
}

export const ApprovalCenter: React.FC<ApprovalCenterProps> = ({ approvals, onRefresh }) => {
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const handleResolve = async (id: string, approved: boolean) => {
    setResolvingId(id);
    try {
      await api.resolveApproval(id, approved, approved ? 'Approved by Store Owner via Dashboard' : 'Rejected by Store Owner');
      onRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setResolvingId(null);
    }
  };

  const pendingList = approvals.filter((a) => a.status === 'PENDING');
  const resolvedList = approvals.filter((a) => a.status !== 'PENDING');

  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Supervisor Approval Center</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic business guardrails pause transactions exceeding credit or price thresholds for owner sign-off.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            {pendingList.length} Pending Actions
          </span>
        </div>
      </div>

      {/* Pending Approvals Grid */}
      <div className="space-y-4">
        {pendingList.map((appr) => (
          <div key={appr.id} className="bg-surface border border-amber-500/40 rounded-3xl p-6 shadow-card space-y-5">
            
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-border">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                    Risk Level: {appr.risk_level}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">Request #{appr.id.slice(0, 8)}</span>
                </div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>{appr.reason}</span>
                </h3>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2.5 shrink-0">
                <button
                  disabled={resolvingId === appr.id}
                  onClick={() => handleResolve(appr.id, false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 hover:border-rose-500/30 text-slate-300 text-xs font-bold border border-border transition-all"
                >
                  Reject Action
                </button>
                <button
                  disabled={resolvingId === appr.id}
                  onClick={() => handleResolve(appr.id, true)}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-extrabold shadow-glow-emerald transition-all"
                >
                  <Check className="w-4 h-4 stroke-[3]" />
                  <span>Approve & Execute</span>
                </button>
              </div>
            </div>

            {/* Context Policy Comparison Card */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-4 rounded-2xl bg-card border border-border space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Merchant / Customer</span>
                <span className="font-bold text-white text-sm block">{appr.customer_name || 'Amit Shah'}</span>
                <span className="text-[11px] text-slate-500">Retailer Account</span>
              </div>

              <div className="p-4 rounded-2xl bg-card border border-border space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Credit Policy Violation</span>
                <span className="font-bold text-amber-400 text-sm block">Limit: ₹10,000.00</span>
                <span className="text-[11px] text-slate-500">Projected: ₹10,500 (105% Utilized)</span>
              </div>

              <div className="p-4 rounded-2xl bg-card border border-border space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Initiating Channel</span>
                <span className="font-bold text-primary text-sm block">Gemini Live Voice Session</span>
                <span className="text-[11px] text-slate-500">Paused before DB commit</span>
              </div>
            </div>

          </div>
        ))}

        {pendingList.length === 0 && (
          <div className="bg-surface border border-border rounded-3xl p-10 text-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-3">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-white">All Guardrails In Good Standing</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              No orders or credit transactions currently exceed policy thresholds. The system is operating autonomously.
            </p>
          </div>
        )}
      </div>

      {/* Resolved History */}
      {resolvedList.length > 0 && (
        <div className="bg-surface border border-border rounded-3xl p-6 shadow-sm space-y-4">
          <h2 className="text-sm font-bold text-white">Audit History of Supervisor Decisions</h2>
          <div className="divide-y divide-border/60">
            {resolvedList.map((res) => (
              <div key={res.id} className="py-3.5 flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-slate-200">{res.reason}</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Customer: <span className="text-slate-300 font-medium">{res.customer_name || 'Customer'}</span>
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                    res.status === 'APPROVED' 
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                      : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                  }`}>
                    {res.status}
                  </span>
                  <span className="block text-[10px] text-slate-500 font-mono mt-1">
                    {res.resolved_at ? new Date(res.resolved_at).toLocaleTimeString() : 'Resolved'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
