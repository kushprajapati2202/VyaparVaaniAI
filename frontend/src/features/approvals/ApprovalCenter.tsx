import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, User, Calendar, FileText } from 'lucide-react';
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
      await api.resolveApproval(id, approved, approved ? 'Approved by Store Owner' : 'Rejected by Store Owner');
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
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <span>Human-in-the-Loop Approval Center</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic business guardrails pause transactions exceeding policy limits for merchant sign-off.
          </p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
          {pendingList.length} Pending Actions
        </span>
      </div>

      {/* Pending Approvals Grid */}
      <div className="space-y-4">
        {pendingList.map((appr) => (
          <div key={appr.id} className="bg-surface border border-amber-500/40 rounded-2xl p-6 shadow-lg shadow-amber-950/20">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-border">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-950 text-red-400 border border-red-800">
                    Risk: {appr.risk_level}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {appr.id.slice(0, 8)}...
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mt-1.5 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>{appr.reason}</span>
                </h3>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  disabled={resolvingId === appr.id}
                  onClick={() => handleResolve(appr.id, false)}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-red-950 hover:text-red-400 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Reject</span>
                </button>
                <button
                  disabled={resolvingId === appr.id}
                  onClick={() => handleResolve(appr.id, true)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-bold shadow-md shadow-emerald-500/20 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approve & Execute</span>
                </button>
              </div>
            </div>

            {/* Context details */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-300">
              <div className="p-3 rounded-xl bg-card border border-border">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Customer</span>
                <span className="font-semibold text-slate-200 mt-0.5 block">{appr.customer_name || 'Amit Shah'}</span>
              </div>
              <div className="p-3 rounded-xl bg-card border border-border">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Trigger Policy</span>
                <span className="font-semibold text-amber-300 mt-0.5 block">Credit Limit Exceeded</span>
              </div>
              <div className="p-3 rounded-xl bg-card border border-border">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Requested Via</span>
                <span className="font-semibold text-cyan-300 mt-0.5 block">Gemini Live Voice Session</span>
              </div>
            </div>
          </div>
        ))}

        {pendingList.length === 0 && (
          <div className="bg-surface border border-border rounded-2xl p-8 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-white">All Clear!</h3>
            <p className="text-xs text-slate-400 mt-1">No orders or credit transactions require supervisor approval right now.</p>
          </div>
        )}
      </div>

      {/* Resolved Approvals History */}
      {resolvedList.length > 0 && (
        <div className="bg-surface border border-border rounded-2xl p-6">
          <h2 className="text-sm font-bold text-white mb-4">Resolved Decisions History</h2>
          <div className="divide-y divide-border/60">
            {resolvedList.map((res) => (
              <div key={res.id} className="py-3 flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-slate-200">{res.reason}</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">Customer: {res.customer_name || 'Customer'}</p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    res.status === 'APPROVED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                  }`}>
                    {res.status}
                  </span>
                  <span className="block text-[10px] text-slate-500 mt-1">
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
