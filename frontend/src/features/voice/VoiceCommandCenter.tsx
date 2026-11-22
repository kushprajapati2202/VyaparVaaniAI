import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Mic, MicOff, Volume2, Sparkles, Send, Zap, Receipt, Gauge, IndianRupee, Radio, ShieldCheck, Ear,
} from 'lucide-react';
import { ActivityEntry, AgentAction, VoiceMessage } from '../../types';
import { VOICE_WS_URL } from '../../services/api';
import { MicStreamer, PcmPlayer, base64ToArrayBuffer, createBrowserRecognizer } from './audio';
import { ParchiCard } from './ParchiCard';
import { ActivityTimeline } from './ActivityTimeline';

interface VoiceCommandCenterProps {
  currentLanguage: string;
  onRefreshData?: () => void;
}

type Mode = 'connecting' | 'live' | 'fallback' | 'offline';

const ECHO_GUARD_RMS = 0.045; // while the agent talks, only forward mic frames louder than this (likely real speech)
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const uid = () => Math.random().toString(36).slice(2);

const SCENARIOS = [
  { category: 'Gujarati order', badge: 'ગુજરાતી', text: 'રાહુલભાઈને 10 કિલો ચોખા અને 5 કિલો ખાંડ આપવાના છે, ખાતામાં લખજો.', tag: 'text-saffron-400 border-saffron-500/30 bg-saffron-500/10' },
  { category: 'Spoken correction', badge: 'Hinglish', text: 'Nahi nahi, chawal 15 kilo kar do.', tag: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
  { category: 'Confirm', badge: 'Execute', text: 'હા, બરાબર છે, કન્ફર્મ કરો.', tag: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
  { category: 'Credit limit → owner', badge: 'Approval', text: 'Amit bhai ko 50 kilo chawal udhaar pe de do.', tag: 'text-rose-400 border-rose-500/30 bg-rose-500/10' },
  { category: 'Ambiguous name', badge: 'Exception', text: 'કિરણભાઈને 2 લીટર તેલ આપવાનું છે.', tag: 'text-violet-300 border-violet-500/30 bg-violet-500/10' },
  { category: 'Khata payment', badge: 'हिन्दी', text: 'महेश प्रोविजन स्टोर के 2000 रुपये UPI से जमा करो।', tag: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
  { category: 'Undo', badge: 'Safety', text: 'Galti ho gayi, last entry undo karo.', tag: 'text-slate-300 border-slate-500/30 bg-slate-500/10' },
  { category: 'Daily sales', badge: 'BI', text: 'આજનું કુલ વેચાણ કેટલું થયું?', tag: 'text-sky-300 border-sky-500/30 bg-sky-500/10' },
];

export const VoiceCommandCenter: React.FC<VoiceCommandCenterProps> = ({ currentLanguage, onRefreshData }) => {
  const [mode, setMode] = useState<Mode>('connecting');
  const [model, setModel] = useState<string>('');
  const [micOn, setMicOn] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [echoGuard, setEchoGuard] = useState(true);
  const [mobileTab, setMobileTab] = useState<'mic' | 'bill'>('mic');
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [partial, setPartial] = useState<{ user: string; agent: string }>({ user: '', agent: '' });
  const [inputUtterance, setInputUtterance] = useState('');
  const [action, setAction] = useState<AgentAction | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [latencies, setLatencies] = useState<number[]>([]);
  const [costUsd, setCostUsd] = useState(0);
  const [biCard, setBiCard] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<PcmPlayer | null>(null);
  const micRef = useRef<MicStreamer | null>(null);
  const recognizerRef = useRef<any>(null);
  const modeRef = useRef<Mode>('connecting');
  const echoGuardRef = useRef(true);
  const reconnectTimerRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const unmountedRef = useRef(false);

  useEffect(() => { echoGuardRef.current = echoGuard; }, [echoGuard]);

  const player = () => {
    if (!playerRef.current) playerRef.current = new PcmPlayer(24000);
    return playerRef.current;
  };

  const addActivity = useCallback((e: Omit<ActivityEntry, 'id' | 'at'>) => {
    setActivity((prev) => [...prev.slice(-150), { ...e, id: uid(), at: now() }]);
  }, []);

  const addMessage = useCallback((role: VoiceMessage['role'], text: string) => {
    setMessages((prev) => [...prev.slice(-80), { id: uid(), role, text, timestamp: now() }]);
  }, []);

  const handleServerEvent = useCallback((data: any) => {
    switch (data.type) {
      case 'session_started':
        modeRef.current = data.mode;
        setMode(data.mode);
        setModel(data.model || data.brain || '');
        setError(null);
        addActivity({ kind: 'info', title: data.mode === 'live' ? `Gemini Live connected (${data.model})` : `Fallback mode: ${data.reason}` });
        break;
      case 'session_resumed':
        addActivity({ kind: 'info', title: 'Gemini Live session resumed (network blip handled)' });
        break;
      case 'context_reset':
        addActivity({ kind: 'info', title: 'Transaction closed: fresh AI context for the next customer (keeps cost per txn flat)' });
        break;
      case 'transcript_partial':
        setPartial((p) => ({ ...p, [data.role]: p[data.role as 'user' | 'agent'] + data.text }));
        break;
      case 'transcript':
        addMessage(data.role, data.interrupted ? `${data.text} …` : data.text);
        setPartial((p) => ({ ...p, [data.role]: '' }));
        break;
      case 'turn_complete':
        setPartial({ user: '', agent: '' });
        break;
      case 'barge_in':
        playerRef.current?.flush();
        setAgentSpeaking(false);
        setPartial((p) => ({ ...p, agent: '' }));
        addActivity({ kind: 'barge_in', title: data.source === 'voice' ? 'Barge-in: user spoke over the agent, playback cut' : 'Agent stopped manually' });
        break;
      case 'latency':
        setLatencies((l) => [...l.slice(-49), data.ms]);
        break;
      case 'usage':
        setCostUsd(data.cost_usd || 0);
        break;
      case 'tool_call':
        addActivity({
          kind: 'tool', title: `${data.tool}()`, ok: data.success, latencyMs: data.latency_ms,
          status: data.error_code || (data.success ? 'OK' : 'ERROR'),
          detail: Object.entries(data.args || {}).map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · '),
        });
        if (['confirm_action', 'undo_last_action'].includes(data.tool) && onRefreshData) onRefreshData();
        break;
      case 'workflow_step':
        addActivity({ kind: 'step', title: data.step, status: data.status, human: data.human, detail: `${data.workflow} · ${data.action_id}` });
        break;
      case 'action_update':
        setAction(data.action);
        if (window.innerWidth < 1024 && data.action.status === 'AWAITING_CONFIRMATION') setMobileTab('bill');
        break;
      case 'exception':
        addActivity({ kind: 'exception', title: `Exception: ${data.code}`, detail: data.message, ok: false });
        break;
      case 'approval_required':
        addActivity({ kind: 'approval', title: `Owner approval requested: ${data.order_number}`, detail: data.reason, human: true });
        onRefreshData?.();
        break;
      case 'approval_resolved':
        addActivity({ kind: 'approval', title: `Owner ${data.approved ? 'APPROVED' : 'REJECTED'} ${data.order_number ?? ''}`, detail: data.approver_notes, human: true });
        onRefreshData?.();
        break;
      case 'bi_card':
        setBiCard(data.metrics);
        break;
      case 'audio_mp3':
        player().playEncoded(base64ToArrayBuffer(data.data)).catch(() => undefined);
        break;
      case 'error':
        setError(data.message || data.code);
        addActivity({ kind: 'exception', title: `Error: ${data.code}`, detail: data.message, ok: false });
        break;
    }
  }, [addActivity, addMessage, onRefreshData]);

  const connectWebSocket = useCallback(() => {
    if (unmountedRef.current) return;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    setMode('connecting');
    const ws = new WebSocket(VOICE_WS_URL);
    ws.binaryType = 'arraybuffer';
    socketRef.current = ws;
    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        handleServerEvent(JSON.parse(event.data));
      } else {
        player().playPcm16(event.data as ArrayBuffer);
        setAgentSpeaking(true);
      }
    };
    ws.onclose = () => {
      modeRef.current = 'offline';
      setMode('offline');
      if (!unmountedRef.current) reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
    };
  }, [handleServerEvent]);

  useEffect(() => {
    unmountedRef.current = false;
    connectWebSocket();
    const speakingPoll = setInterval(() => setAgentSpeaking(!!playerRef.current?.playing), 200);
    return () => {
      unmountedRef.current = true;
      clearInterval(speakingPoll);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      micRef.current?.stop();
      recognizerRef.current?.stop?.();
      socketRef.current?.close();
      playerRef.current?.close();
      playerRef.current = null;
    };
  }, [connectWebSocket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages, partial]);

  const sendJson = (obj: any) => {
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  };

  const sendUtterance = (text: string) => {
    if (!text.trim()) return;
    player().resume();
    sendJson({ type: 'user_text', text });
    setInputUtterance('');
  };

  const startMic = async () => {
    setError(null);
    await player().resume();
    if (modeRef.current === 'fallback') {
      const rec = createBrowserRecognizer(currentLanguage, (t) => sendUtterance(t));
      if (!rec) { setError('This browser has no speech recognition. Use Chrome, or type.'); return; }
      recognizerRef.current = rec;
      rec.start();
      setMicOn(true);
      return;
    }
    try {
      const mic = new MicStreamer();
      await mic.start(({ pcm, rms }) => {
        setMicLevel(rms);
        const ws = socketRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        // Echo guard: while agent audio plays, quiet frames are probably speaker echo -> send silence instead
        if (echoGuardRef.current && playerRef.current?.playing && rms < ECHO_GUARD_RMS) {
          ws.send(new ArrayBuffer(pcm.byteLength));
        } else {
          ws.send(pcm);
        }
      });
      micRef.current = mic;
      setMicOn(true);
    } catch (e: any) {
      setError(`Microphone unavailable: ${e?.message || e}`);
    }
  };

  const stopMic = () => {
    micRef.current?.stop();
    micRef.current = null;
    recognizerRef.current?.stop?.();
    recognizerRef.current = null;
    setMicOn(false);
    setMicLevel(0);
    if (modeRef.current === 'live') sendJson({ type: 'audio_stream_end' });
  };

  const stopAgent = () => {
    playerRef.current?.flush();
    sendJson({ type: 'user_interruption' });
  };

  const lastLatency = latencies.length ? latencies[latencies.length - 1] : null;
  const avgLatency = latencies.length ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : null;
  const modeBadge = {
    connecting: { text: 'Connecting…', cls: 'bg-slate-700 text-slate-300', dot: 'bg-slate-400' },
    live: { text: `Gemini Live · ${model}`, cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30', dot: 'bg-emerald-400 animate-pulse' },
    fallback: { text: `Fallback · ${model}`, cls: 'bg-amber-500/10 text-amber-300 border-amber-500/30', dot: 'bg-amber-400' },
    offline: { text: 'Offline · retrying', cls: 'bg-rose-500/10 text-rose-300 border-rose-500/30', dot: 'bg-rose-400' },
  }[mode];

  return (
    <div className="max-w-[1400px] mx-auto p-3 sm:p-6 space-y-4 sm:space-y-6">
      {/* Status bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 bg-surface border border-border rounded-2xl p-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-saffron-500/15 border border-saffron-500/30 flex items-center justify-center text-saffron-400 shrink-0"><Mic className="w-5 h-5" /></div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-white tracking-tight">Vernacular Voice Counter</h1>
            <p className="text-xs text-slate-400 line-clamp-1">Speak Gujarati, Hindi, Hinglish or English. Interrupt any time.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
          <span className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border ${modeBadge.cls}`}><span className={`w-2 h-2 rounded-full ${modeBadge.dot}`} />{modeBadge.text}</span>
          <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-border bg-background text-cyan-300" title="Time from the end of your speech to the agent's first audio">
            <Gauge className="w-3.5 h-3.5" />{lastLatency != null ? `${lastLatency} ms` : '- ms'}{avgLatency != null && <span className="text-slate-500">avg {avgLatency}</span>}
          </span>
          <span className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-border bg-background text-slate-300" title="Gemini Live token cost this session">
            <IndianRupee className="w-3.5 h-3.5" />{(costUsd * 84).toFixed(2)} AI cost
          </span>
          <button onClick={() => setEchoGuard((v) => !v)} className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl border ${echoGuard ? 'border-emerald-500/30 text-emerald-300' : 'border-border text-slate-500'}`} title="Suppress speaker echo while the agent talks (use without headphones)">
            <ShieldCheck className="w-3.5 h-3.5" />Echo guard {echoGuard ? 'on' : 'off'}
          </button>
          <button onClick={stopAgent} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 font-semibold active:scale-95">
            <Zap className="w-3.5 h-3.5" />Stop agent
          </button>
        </div>
      </div>

      {error && <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">{error}</div>}

      {/* Mobile tabs */}
      <div className="lg:hidden flex items-center bg-card p-1 rounded-2xl border border-border">
        <button onClick={() => setMobileTab('mic')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold ${mobileTab === 'mic' ? 'bg-saffron-500 text-slate-950' : 'text-slate-400'}`}><Mic className="w-4 h-4" />Voice</button>
        <button onClick={() => setMobileTab('bill')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold ${mobileTab === 'bill' ? 'bg-saffron-500 text-slate-950' : 'text-slate-400'}`}>
          <Receipt className="w-4 h-4" />Slip & activity{action?.status === 'AWAITING_CONFIRMATION' && <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT */}
        <div className={`lg:col-span-7 space-y-5 ${mobileTab === 'bill' ? 'hidden lg:block' : 'block'}`}>
          <div className="bg-gradient-to-b from-surface to-card border border-border rounded-3xl p-5 sm:p-6 shadow-card relative overflow-hidden">
            <div className="flex flex-col items-center justify-center py-3 relative z-10">
              <div className="relative mb-4">
                {micOn && <div className="absolute inset-0 rounded-full bg-saffron-500/20 voice-ripple" />}
                <button
                  onClick={micOn ? stopMic : startMic}
                  disabled={mode === 'connecting' || mode === 'offline'}
                  className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-2xl relative z-10 disabled:opacity-40 ${
                    micOn ? 'bg-gradient-to-tr from-rose-600 to-rose-500 text-white scale-105' : 'bg-gradient-to-tr from-saffron-500 to-amber-500 text-slate-950 shadow-glow-saffron hover:scale-105 active:scale-95'}`}
                >
                  {micOn ? <MicOff className="w-8 h-8 sm:w-9 sm:h-9" /> : <Mic className="w-8 h-8 sm:w-9 sm:h-9" />}
                  <span className="text-[9px] sm:text-[10px] font-bold mt-1 tracking-tight">{micOn ? 'TAP TO END' : 'TAP & TALK'}</span>
                </button>
              </div>
              <p className="text-xs font-semibold text-center min-h-[1rem]">
                {agentSpeaking ? (
                  <span className="text-cyan-300 flex items-center gap-2"><Volume2 className="w-4 h-4" />Agent speaking. Talk over it to interrupt.</span>
                ) : micOn ? (
                  <span className="text-saffron-400 flex items-center gap-2"><Ear className="w-4 h-4" />{mode === 'live' ? 'Listening continuously (hands-free)' : 'Listening (browser speech recognition)'}</span>
                ) : (
                  <span className="text-slate-300">Tap once and keep talking. No need to hold.</span>
                )}
              </p>
              <div className="flex items-center gap-1 mt-3.5 h-8 px-2" aria-hidden>
                {[...Array(24)].map((_, i) => {
                  const lvl = micOn ? Math.min(1, micLevel * 8) : agentSpeaking ? 0.5 : 0;
                  return <div key={i} className={`w-1 rounded-full transition-all duration-100 ${agentSpeaking ? 'bg-cyan-400' : 'bg-saffron-400'}`}
                    style={{ height: `${Math.max(4, lvl * (12 + 16 * Math.abs(Math.sin(i * 0.7 + Date.now() / 300))))}px`, opacity: lvl ? 0.9 : 0.25 }} />;
                })}
              </div>
            </div>
            <div className="pt-4 border-t border-border flex items-center gap-2">
              <input
                type="text" value={inputUtterance} onChange={(e) => setInputUtterance(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendUtterance(inputUtterance)}
                placeholder="Too noisy? Type instead: 'રાહુલને 10 કિલો ચોખા આપો'"
                className="flex-1 min-w-0 bg-background/80 border border-border rounded-xl px-3 sm:px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-saffron-500"
              />
              <button onClick={() => sendUtterance(inputUtterance)} className="px-3.5 py-2.5 rounded-xl bg-saffron-500 hover:bg-saffron-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 shrink-0"><Send className="w-3.5 h-3.5" />Send</button>
            </div>
          </div>

          {/* Conversation */}
          <div className="bg-surface border border-border rounded-2xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-border text-xs">
              <span className="font-bold text-white flex items-center gap-2"><Radio className="w-4 h-4 text-saffron-400" />Live conversation</span>
              <span className="text-slate-500 text-[11px]">Gemini transcription · real-time</span>
            </div>
            <div className="max-h-72 overflow-y-auto space-y-3 pr-1">
              {messages.length === 0 && !partial.user && !partial.agent && <p className="text-[11px] text-slate-500 text-center py-6">Waiting for the agent's greeting…</p>}
              {messages.map((m) => <Bubble key={m.id} role={m.role} text={m.text} time={m.timestamp} />)}
              {partial.user && <Bubble role="user" text={partial.user} time="…" ghost />}
              {partial.agent && <Bubble role="agent" text={partial.agent} time="…" ghost />}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Scenarios */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-saffron-400" />Try saying (or tap to send as text)</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {SCENARIOS.map((sc) => (
                <button key={sc.text} onClick={() => sendUtterance(sc.text)} className="text-left p-3 rounded-2xl bg-surface border border-border hover:border-saffron-500/40 hover:bg-card transition-all group">
                  <div className="flex items-center justify-between mb-1 gap-2">
                    <span className="text-[10px] font-bold text-slate-400">{sc.category}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sc.tag}`}>{sc.badge}</span>
                  </div>
                  <p className="text-xs font-semibold text-slate-200 group-hover:text-saffron-300 line-clamp-2 break-words">“{sc.text}”</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className={`lg:col-span-5 space-y-6 ${mobileTab === 'mic' ? 'hidden lg:block' : 'block'}`}>
          <ParchiCard action={action} onSay={sendUtterance} />
          {biCard && (
            <div className="bg-surface border border-cyan-500/30 rounded-2xl p-4 grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-2 font-bold text-cyan-300">Today at the counter</div>
              <Stat label="Sales" value={`₹${biCard.total_sales_today.toLocaleString('en-IN')}`} />
              <Stat label="Orders" value={biCard.orders_count_today} />
              <Stat label="Payments in" value={`₹${biCard.payments_received_today.toLocaleString('en-IN')}`} />
              <Stat label="Pending approvals" value={biCard.pending_approvals_count} />
            </div>
          )}
          <ActivityTimeline entries={activity} />
        </div>
      </div>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="p-2.5 rounded-xl bg-background border border-border"><div className="text-[10px] text-slate-400">{label}</div><div className="font-mono font-bold text-white">{value}</div></div>
);

const Bubble: React.FC<{ role: VoiceMessage['role']; text: string; time: string; ghost?: boolean }> = ({ role, text, time, ghost }) => {
  if (role === 'system') {
    return <div className="text-center py-1"><span className="inline-block px-3 py-1 rounded-full text-[10px] font-mono bg-background border border-border text-amber-300 max-w-full break-words">{text}</span></div>;
  }
  const isUser = role === 'user';
  return (
    <div className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''} ${ghost ? 'opacity-60' : ''}`}>
      <div className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-[10px] font-bold ${isUser ? 'bg-slate-700 text-slate-200' : 'bg-saffron-500/20 text-saffron-400 border border-saffron-500/40'}`}>{isUser ? 'તમે' : 'AI'}</div>
      <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed break-words ${isUser ? 'bg-saffron-500 text-slate-950 font-medium rounded-tr-none' : 'bg-card border border-border text-slate-200 rounded-tl-none'}`}>
        <p>{text}</p>
        <span className={`block text-[9px] mt-1 ${isUser ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>{time}</span>
      </div>
    </div>
  );
};
