import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Cpu, Hand, UserCheck, Zap } from 'lucide-react';
import { ActivityEntry } from '../../types';

const ICONS: Record<ActivityEntry['kind'], React.ReactNode> = {
  step: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
  tool: <Cpu className="w-3.5 h-3.5 text-cyan-400" />,
  exception: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
  barge_in: <Zap className="w-3.5 h-3.5 text-amber-300" />,
  approval: <UserCheck className="w-3.5 h-3.5 text-rose-300" />,
  info: <Activity className="w-3.5 h-3.5 text-slate-400" />,
};

export const ActivityTimeline: React.FC<{ entries: ActivityEntry[] }> = ({ entries }) => {
  const humanCount = entries.filter((e) => e.human).length;
  const toolCount = entries.filter((e) => e.kind === 'tool').length;
  const exceptionCount = entries.filter((e) => e.kind === 'exception').length;

  return (
    <div className="bg-surface border border-border rounded-2xl p-4 sm:p-5 space-y-3">
      <div className="flex items-center justify-between pb-3 border-b border-border text-xs gap-2">
        <span className="font-bold text-white flex items-center gap-2"><Activity className="w-4 h-4 text-saffron-400" />Agent activity</span>
        <span className="text-[10px] font-mono text-slate-400 flex gap-2 flex-wrap justify-end">
          <span>{toolCount} tool calls</span>
          <span className="text-amber-300">{exceptionCount} exceptions</span>
          <span className="text-rose-300">{humanCount} human touchpoints</span>
        </span>
      </div>
      <ol className="max-h-80 overflow-y-auto space-y-1.5 pr-1">
        {entries.length === 0 && <li className="text-[11px] text-slate-500 py-4 text-center">Tool calls, decisions and human checkpoints appear here live.</li>}
        {[...entries].reverse().map((e) => (
          <li key={e.id} className={`flex items-start gap-2 text-[11px] rounded-xl px-2.5 py-1.5 border ${e.human ? 'border-rose-500/30 bg-rose-500/5' : 'border-transparent'}`}>
            <span className="mt-0.5 shrink-0">{e.human ? <Hand className="w-3.5 h-3.5 text-rose-300" /> : ICONS[e.kind]}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`font-semibold ${e.ok === false ? 'text-amber-300' : 'text-slate-200'}`}>{e.title}</span>
                {e.human && <span className="text-[9px] font-bold px-1.5 rounded bg-rose-500/20 text-rose-300">HUMAN</span>}
                {e.status && <span className="text-[9px] font-mono text-slate-500">{e.status}</span>}
                {e.latencyMs != null && <span className="text-[9px] font-mono text-cyan-300">{e.latencyMs} ms</span>}
              </div>
              {e.detail && <div className="text-slate-400 break-words">{e.detail}</div>}
            </div>
            <span className="text-[9px] text-slate-600 font-mono shrink-0">{e.at}</span>
          </li>
        ))}
      </ol>
    </div>
  );
};
