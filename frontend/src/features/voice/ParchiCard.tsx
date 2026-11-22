import React from 'react';
import { CheckCircle2, Receipt, ShieldAlert, User, Undo2, XCircle, PenLine, AlertTriangle, Wallet } from 'lucide-react';
import { AgentAction } from '../../types';

interface Props {
  action: AgentAction | null;
  onSay: (text: string) => void;
}

const inr = (n?: number | null) => `₹${(n ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

const STAMPS: Record<string, { label: string; cls: string }> = {
  AWAITING_CONFIRMATION: { label: '● READ-BACK · SAY “HAAN”', cls: 'bg-amber-500/10 border-amber-500/30 text-amber-300' },
  PENDING_APPROVAL: { label: '⚠ OWNER APPROVAL', cls: 'bg-rose-500/20 border-rose-500/40 text-rose-300 -rotate-2' },
  EXECUTED: { label: '✓ CONFIRMED', cls: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 rotate-3' },
  CANCELLED: { label: '✕ CANCELLED', cls: 'bg-slate-700/40 border-border text-slate-400' },
  UNDONE: { label: '↶ UNDONE', cls: 'bg-slate-700/40 border-border text-slate-300' },
  REJECTED: { label: '✕ OWNER REJECTED', cls: 'bg-rose-500/20 border-rose-500/40 text-rose-300' },
};

export const ParchiCard: React.FC<Props> = ({ action, onSay }) => {
  const stamp = action ? STAMPS[action.status] : null;
  const isOrder = action?.kind === 'ORDER';
  const result = action?.result || {};

  return (
    <div className="parchi-paper border border-border rounded-3xl p-5 sm:p-6 shadow-card space-y-5">
      <div className="flex items-start justify-between pb-4 border-b border-border/80 gap-3">
        <div>
          <div className="flex items-center gap-1.5 text-saffron-400">
            <Receipt className="w-4 h-4" />
            <span className="text-[11px] font-bold uppercase tracking-wider">કાચી પાવતી • COUNTER SLIP</span>
          </div>
          <h2 className="text-base font-bold text-white mt-1">Shree Ganesh Kirana</h2>
          <p className="text-[11px] text-slate-400">
            {action ? `${action.kind === 'ORDER' ? 'Order' : 'Khata payment'} · ${action.action_id}` : 'Station Road, Ahmedabad'}
            {result.order_number ? ` · ${result.order_number}` : ''}
          </p>
        </div>
        {stamp && (
          <div className={`px-3 py-1 rounded-xl border text-[11px] font-bold tracking-tight text-right ${stamp.cls}`}>{stamp.label}</div>
        )}
      </div>

      {!action ? (
        <div className="py-8 text-center text-slate-500 text-xs border border-dashed border-border rounded-2xl">
          <Receipt className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="font-medium text-slate-400">No active bill</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Speak an order or payment. The agent fills this from the real database.</p>
        </div>
      ) : (
        <>
          <div className="p-3.5 rounded-2xl bg-background/60 border border-border space-y-1">
            <div className="flex items-center justify-between text-xs gap-2">
              <span className="text-slate-400 flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-saffron-400" />Customer</span>
              <span className="font-bold text-white text-right">{action.customer_name}</span>
            </div>
            <div className="flex items-center justify-between text-xs gap-2">
              <span className="text-slate-400">{isOrder ? 'Payment mode' : 'Mode'}</span>
              <span className="font-mono text-saffron-400 font-semibold">
                {isOrder ? (action.payment_method === 'CREDIT' ? 'Khata (ઉધાર)' : action.payment_method) : action.mode}
              </span>
            </div>
            {action.corrections > 0 && (
              <div className="flex items-center gap-1.5 text-[11px] text-amber-300 pt-1">
                <PenLine className="w-3.5 h-3.5" /> Spoken correction applied ×{action.corrections}
              </div>
            )}
          </div>

          {isOrder ? (
            <div className="space-y-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Items ({action.items?.length ?? 0})</div>
              <div className="divide-y divide-border/60">
                {action.items?.map((it) => (
                  <div key={it.product_name} className="py-2.5 flex items-center justify-between text-xs gap-2">
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-200">{it.product_name}</div>
                      <div className="text-[11px] text-slate-400">{it.quantity} {it.unit} × {inr(it.unit_price)}</div>
                    </div>
                    <div className="font-bold font-mono text-white text-sm">{inr(it.subtotal)}</div>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between text-sm font-bold pt-3 border-t-2 border-dashed border-border">
                <span className="text-white">Total (કુલ રકમ)</span>
                <span className="text-lg text-saffron-400 font-mono">{inr(action.total_amount)}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between"><span className="text-slate-400 flex items-center gap-1.5"><Wallet className="w-3.5 h-3.5" />Amount received (જમા)</span><span className="text-lg font-mono font-bold text-saffron-400">{inr(action.amount)}</span></div>
              <div className="flex items-center justify-between"><span className="text-slate-400">Outstanding before</span><span className="font-mono text-slate-200">{inr(action.outstanding_before)}</span></div>
              <div className="flex items-center justify-between"><span className="text-slate-400">Balance after</span><span className="font-mono text-white font-semibold">{inr(result.updated_outstanding_balance ?? action.projected_balance)}</span></div>
            </div>
          )}

          {action.warnings?.length > 0 && (
            <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-200 space-y-1">
              {action.warnings.map((w) => (
                <div key={w} className="flex gap-1.5"><AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />{w}</div>
              ))}
            </div>
          )}

          {(action.status === 'PENDING_APPROVAL' || (action.status === 'AWAITING_CONFIRMATION' && action.requires_approval)) && (
            <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-rose-400"><ShieldAlert className="w-4 h-4 shrink-0" />Needs owner approval</div>
              <p className="text-[11px] leading-relaxed text-slate-300">{action.approval_reason || result.approval_reason}</p>
              <span className="inline-block text-[10px] font-bold bg-rose-500/20 px-2 py-0.5 rounded text-rose-300">
                {action.status === 'PENDING_APPROVAL' ? 'Waiting in Approval Center: agent will announce the decision' : 'Will be routed to the Approval Center on confirm'}
              </span>
            </div>
          )}

          {action.status === 'EXECUTED' && (
            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-bold">Saved to {isOrder ? 'orders, stock & khata' : 'khata ledger'}</span>
                {result.updated_outstanding_balance != null && (
                  <p className="text-[11px] text-slate-400">Khata balance now {inr(result.updated_outstanding_balance)}</p>
                )}
              </div>
            </div>
          )}

          <div className="pt-1 flex flex-col sm:flex-row items-stretch gap-2">
            {action.status === 'AWAITING_CONFIRMATION' && (
              <>
                <button onClick={() => onSay('હા, કન્ફર્મ કરો')} className="sm:flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all">
                  <CheckCircle2 className="w-4 h-4" /> Haan, confirm
                </button>
                <button onClick={() => onSay('Nahi, cancel karo')} className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs border border-border flex items-center justify-center gap-1.5">
                  <XCircle className="w-4 h-4" /> Cancel
                </button>
              </>
            )}
            {(action.status === 'EXECUTED' || action.status === 'PENDING_APPROVAL') && (
              <button onClick={() => onSay('Galti ho gayi, last entry undo karo')} className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs border border-border flex items-center justify-center gap-1.5">
                <Undo2 className="w-4 h-4" /> Undo (say “undo”)
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
};
