import React, { useEffect, useState } from 'react';
import { BarChart3, Gauge, Hand, IndianRupee, Languages, ShieldAlert, Timer, RefreshCw } from 'lucide-react';
import { DailyMetrics, ImpactMetrics } from '../../types';
import { api } from '../../services/api';

interface AnalyticsPageProps {
  metrics: DailyMetrics | null;
}

const LANG_LABELS: Record<string, string> = {
  gu: 'ગુજરાતી', hi: 'हिन्दी', en: 'English', hinglish: 'Hinglish', gujlish: 'Gujlish', ta: 'தமிழ்', tanglish: 'Tanglish',
  mr: 'मराठी', bn: 'বাংলা', te: 'తెలుగు', kn: 'ಕನ್ನಡ', ml: 'മലയാളം', pa: 'ਪੰਜਾਬੀ', other: 'Other',
};

const fmt = (v: number | null | undefined, suffix = '') => (v == null ? '-' : `${v.toLocaleString('en-IN')}${suffix}`);

export const AnalyticsPage: React.FC<AnalyticsPageProps> = () => {
  const [impact, setImpact] = useState<ImpactMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setImpact(await api.getImpact()); } catch { /* backend offline */ } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const m = impact;
  const langTotal = m ? Object.values(m.languages).reduce((a, b) => a + b, 0) : 0;
  const voiceSec = m?.avg_voice_txn_seconds;
  const savedPct = m && voiceSec ? Math.round(100 * (1 - voiceSec / m.manual_seconds_per_txn)) : null;

  return (
    <div className="max-w-[1400px] mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><BarChart3 className="w-5 h-5 text-saffron-400" />Agent Impact & Unit Economics</h1>
          <p className="text-xs text-slate-400 mt-1">Every number below is measured from real voice-agent activity in this deployment. Assumptions are labelled.</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-saffron-500/15 text-saffron-400 border border-saffron-500/30">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />Live · {m?.voice_sessions ?? 0} voice sessions
        </button>
      </div>

      {!m || m.transactions_completed + m.undone === 0 ? (
        <div className="p-6 rounded-3xl bg-surface border border-dashed border-border text-center text-xs text-slate-400">
          No voice transactions yet. Complete an order or payment on the Voice Counter and the metrics fill in automatically.
        </div>
      ) : null}

      {/* Headline KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi icon={<BarChart3 className="w-4 h-4" />} label="Transactions completed by voice" value={fmt(m?.transactions_completed)}
          sub={`${fmt(m?.orders_completed)} orders · ${fmt(m?.payments_completed)} payments · ${fmt(m?.undone)} undone`} tone="text-saffron-400" />
        <Kpi icon={<Hand className="w-4 h-4" />} label="Straight-through automation" value={fmt(m?.automation_rate_percent, '%')}
          sub={`${fmt(m?.human_touch_rate_percent, '%')} routed to owner approval (${fmt(m?.approvals_required)})`} tone="text-emerald-400" />
        <Kpi icon={<Gauge className="w-4 h-4" />} label="Voice response latency" value={fmt(m?.avg_response_latency_ms, ' ms')}
          sub={`p90 ${fmt(m?.p90_response_latency_ms, ' ms')} · tools avg ${fmt(m?.avg_tool_latency_ms, ' ms')}`} tone="text-cyan-300" />
        <Kpi icon={<ShieldAlert className="w-4 h-4" />} label="Exceptions caught before writing" value={fmt(m?.exceptions_caught)}
          sub={`${fmt(m?.corrections_handled)} spoken corrections handled`} tone="text-amber-300" />
      </div>

      {/* Time & money */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-5 sm:p-6 rounded-3xl bg-surface border border-border space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2"><Timer className="w-4 h-4 text-saffron-400" />Time per transaction</h2>
          <Bar label="Manual (khata diary + billing app) · assumption" seconds={m?.manual_seconds_per_txn ?? 0} max={m?.manual_seconds_per_txn ?? 1} cls="bg-slate-500" />
          <Bar label="Voice: proposal → confirmed · measured" seconds={voiceSec ?? 0} max={m?.manual_seconds_per_txn ?? 1} cls="bg-saffron-500" />
          <p className="text-xs text-slate-300">
            {savedPct != null ? <><b className="text-emerald-400">{savedPct}% faster</b>, {fmt(m?.time_saved_minutes)} min saved so far ≈ ₹{fmt(m?.labour_saved_inr)} of counter time.</> : 'Waiting for the first measured transaction.'}
          </p>
        </div>

        <div className="p-5 sm:p-6 rounded-3xl bg-surface border border-border space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2"><IndianRupee className="w-4 h-4 text-saffron-400" />Unit economics (Gemini Live)</h2>
          <Row k="Total AI cost so far (token usage × list price)" v={`₹${fmt(m?.total_ai_cost_inr)}`} />
          <Row k="AI cost per completed transaction" v={m?.cost_per_transaction_inr != null ? `₹${m.cost_per_transaction_inr}` : '-'} />
          <Row k="Shop subscription (pricing assumption)" v={`₹${fmt(m?.subscription_price_inr)}/month`} />
          <Row k="Transactions/month covered by one subscription" v={fmt(m?.breakeven_txns_per_month)} />
          <p className="text-[11px] text-slate-500 pt-1">
            Prices: {m?.assumptions?.live_model} audio in ${m?.assumptions?.price_input_audio_usd_per_m}/M tok, audio out ${m?.assumptions?.price_output_audio_usd_per_m}/M tok, ₹{m?.assumptions?.usd_to_inr}/USD. Cost is recorded when a voice session ends.
          </p>
        </div>
      </div>

      {/* Languages & exceptions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-5 sm:p-6 rounded-3xl bg-surface border border-border space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2"><Languages className="w-4 h-4 text-saffron-400" />Languages used (as detected by Gemini)</h2>
          {langTotal === 0 && <p className="text-xs text-slate-500">No data yet.</p>}
          {m && Object.entries(m.languages).map(([code, n]) => (
            <Bar key={code} label={`${LANG_LABELS[code] ?? code} · ${n}`} seconds={n} max={langTotal} cls="bg-emerald-500" unit="" />
          ))}
        </div>
        <div className="p-5 sm:p-6 rounded-3xl bg-surface border border-border space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-amber-300" />Exceptions handled (errors avoided)</h2>
          {m && Object.keys(m.exceptions_by_code).length === 0 && <p className="text-xs text-slate-500">No exceptions yet.</p>}
          {m && Object.entries(m.exceptions_by_code).map(([code, n]) => <Row key={code} k={code.replace(/_/g, ' ').toLowerCase()} v={String(n)} />)}
        </div>
      </div>
    </div>
  );
};

const Kpi: React.FC<{ icon: React.ReactNode; label: string; value: string; sub: string; tone: string }> = ({ icon, label, value, sub, tone }) => (
  <div className="p-4 sm:p-5 rounded-3xl bg-surface border border-border">
    <div className="text-[11px] font-semibold text-slate-400 mb-1 flex items-center gap-1.5">{icon}{label}</div>
    <div className={`text-2xl sm:text-3xl font-display font-bold ${tone}`}>{value}</div>
    <p className="text-[11px] text-slate-500 mt-1.5">{sub}</p>
  </div>
);

const Row: React.FC<{ k: string; v: string }> = ({ k, v }) => (
  <div className="flex items-center justify-between text-xs gap-3 border-b border-border/60 pb-2"><span className="text-slate-400 capitalize-first">{k}</span><span className="font-mono font-semibold text-white">{v}</span></div>
);

const Bar: React.FC<{ label: string; seconds: number; max: number; cls: string; unit?: string }> = ({ label, seconds, max, cls, unit = ' s' }) => (
  <div className="space-y-1">
    <div className="flex justify-between text-[11px] text-slate-400"><span>{label}</span><span className="font-mono text-slate-200">{unit ? `${seconds}${unit}` : ''}</span></div>
    <div className="h-2.5 rounded-full bg-background overflow-hidden"><div className={`h-full rounded-full ${cls}`} style={{ width: `${Math.min(100, (100 * seconds) / Math.max(max, 1))}%` }} /></div>
  </div>
);
