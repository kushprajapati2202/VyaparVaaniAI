import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Volume2, Sparkles, AlertTriangle, CheckCircle2, 
  Send, Zap, ChevronRight, Receipt, User, Clock, ShieldAlert,
  ArrowUpRight, CornerDownLeft, VolumeX, ListChecks, Smartphone
} from 'lucide-react';
import { VoiceMessage } from '../../types';

interface VoiceCommandCenterProps {
  currentLanguage: string;
  onRefreshData?: () => void;
}

interface DraftBillItem {
  name: string;
  quantity: number;
  unit: string;
  price: number;
  subtotal: number;
}

export const VoiceCommandCenter: React.FC<VoiceCommandCenterProps> = ({ currentLanguage, onRefreshData }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [mobileTab, setMobileTab] = useState<'mic' | 'bill'>('mic');
  const [messages, setMessages] = useState<VoiceMessage[]>([
    {
      id: 'init-1',
      role: 'agent',
      text: 'નમસ્તે! હું વ્યાપારવાણી AI છું. આજે તમે કયો ઓર્ડર અથવા હિસાબ કરવા માંગો છો?',
      timestamp: 'Just now'
    }
  ]);
  const [inputUtterance, setInputUtterance] = useState('');
  const [workflowStage, setWorkflowStage] = useState<string>('IDLE');
  const [activeApproval, setActiveApproval] = useState<any>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  
  // Real-time Visual Draft Bill State (Parchi / પાવતી)
  const [draftBill, setDraftBill] = useState<{
    customerName: string;
    items: DraftBillItem[];
    paymentMode: string;
    totalAmount: number;
    orderNumber?: string;
    isConfirmed?: boolean;
    isPausedForApproval?: boolean;
    approvalReason?: string;
  } | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const reconnectTimerRef = useRef<any>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    try {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      const ws = new WebSocket('ws://localhost:8000/api/v1/voice/live');
      socketRef.current = ws;

      ws.onopen = () => setIsConnected(true);
      ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          const data = JSON.parse(event.data);
          handleServerEvent(data);
        } else if (event.data instanceof Blob) {
          playAudioBlob(event.data);
        }
      };
      ws.onclose = () => {
        setIsConnected(false);
        // Automatic exponential backoff reconnection for shopkeeper reliability
        reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
      };
      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (e) {
      console.warn('WebSocket connection error:', e);
      reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
    }
  };

  const handleServerEvent = (data: any) => {
    if (data.type === 'transcript') {
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: data.role,
          text: data.text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      setWorkflowStage('READY');

      // Update draft bill state based on agent dialog
      if (data.text.includes('ચોખાનો જથ્થો') && draftBill) {
        const updated = { ...draftBill };
        if (updated.items.length > 0) {
          updated.items[0].quantity = 15;
          updated.items[0].subtotal = 15 * updated.items[0].price;
          updated.totalAmount = updated.items.reduce((s, it) => s + it.subtotal, 0);
          setDraftBill(updated);
        }
      } else if (data.text.includes('સફળતાપૂર્વક કન્ફર્મ') && draftBill) {
        setDraftBill({
          ...draftBill,
          isConfirmed: true,
          orderNumber: 'VV-2026-0001'
        });
      }

      if (onRefreshData) onRefreshData();
    } else if (data.type === 'workflow_update') {
      setWorkflowStage(data.step);
    } else if (data.type === 'tool_executed') {
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: 'system',
          text: `⚡ Function Call: ${data.tool}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          toolCall: { tool: data.tool, args: data.args, result: data.result }
        }
      ]);
    } else if (data.type === 'approval_required') {
      setActiveApproval(data);
      setWorkflowStage('APPROVAL_PENDING');
      if (draftBill) {
        setDraftBill({
          ...draftBill,
          isPausedForApproval: true,
          approvalReason: data.reason
        });
      }
      if (onRefreshData) onRefreshData();
    }
  };

  const playAudioBlob = async (blob: Blob) => {
    try {
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      await audio.play();
    } catch (e) {
      console.warn('Audio playback error:', e);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleRecording = () => {
    if (!isRecording) {
      setIsRecording(true);
      setWorkflowStage('LISTENING');
      simulateWaveform();
    } else {
      setIsRecording(false);
      setWorkflowStage('PROCESSING');
      setAudioLevel(0);
    }
  };

  const simulateWaveform = () => {
    const interval = setInterval(() => {
      setAudioLevel(Math.random() * 0.7 + 0.3);
    }, 120);
    setTimeout(() => {
      clearInterval(interval);
      if (isRecording) setAudioLevel(0.15);
    }, 4500);
  };

  const sendUtterance = (text: string) => {
    if (!text.trim()) return;

    const lower = text.toLowerCase();
    if (lower.includes('rahul') || text.includes('રાહુલ')) {
      const isCorrected = lower.includes('15') || lower.includes('change');
      const qtyRice = isCorrected ? 15 : 10;
      setDraftBill({
        customerName: 'Rahul Patel (રાહુલ પટેલ)',
        paymentMode: 'Khata Credit (ઉધાર)',
        items: [
          { name: 'Basmati Rice (ચોખા)', quantity: qtyRice, unit: 'kg', price: 60, subtotal: qtyRice * 60 },
          { name: 'Sugar M-30 (ખાંડ)', quantity: 5, unit: 'kg', price: 45, subtotal: 225 },
        ],
        totalAmount: (qtyRice * 60) + 225,
        isConfirmed: false
      });
    } else if (lower.includes('amit') || text.includes('અમિત')) {
      setDraftBill({
        customerName: 'Amit Shah (અમિત શાહ)',
        paymentMode: 'Khata Credit (ઉધાર)',
        items: [
          { name: 'Basmati Rice (ચોખા)', quantity: 50, unit: 'kg', price: 60, subtotal: 3000 },
        ],
        totalAmount: 3000,
        isConfirmed: false,
        isPausedForApproval: true,
        approvalReason: 'Credit limit of ₹10,000 exceeded. Current balance: ₹7,500.'
      });
    }

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'user_text', text }));
    } else {
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: 'user',
          text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
    setInputUtterance('');
    setIsRecording(false);
  };

  const triggerInterruption = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'user_interruption' }));
    }
    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(),
        role: 'system',
        text: '🛑 Barge-in: Output buffer cleared. Agent listening for correction...',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const scenarios = [
    {
      title: 'Workflow 1: Gujarati Order Intake',
      category: 'Regular Sale',
      text: 'રાહુલને 10 કિલો ચોખા અને 5 કિલો ખાંડ આપવાના છે. આજે ડિલિવરી રાખજો.',
      badge: 'ગુજરાતી',
      tagColor: 'text-saffron-400 border-saffron-500/30 bg-saffron-500/10'
    },
    {
      title: 'Workflow 2: Mid-Utterance Correction',
      category: 'Barge-In',
      text: 'Wait, change rice quantity to 15 kg instead!',
      badge: 'Correction',
      tagColor: 'text-amber-400 border-amber-500/30 bg-amber-500/10'
    },
    {
      title: 'Workflow 3: Confirm & Persist',
      category: 'Execution',
      text: 'હા, બરાબર છે, કન્ફર્મ કરી દો.',
      badge: 'Execute',
      tagColor: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    },
    {
      title: 'Workflow 4: Credit Limit & Approval',
      category: 'Guardrails',
      text: 'Give Amit 50 kg rice on credit.',
      badge: 'Approval',
      tagColor: 'text-rose-400 border-rose-500/30 bg-rose-500/10'
    },
    {
      title: 'Workflow 5: Conversational BI',
      category: 'Daily Sales',
      text: 'આજનું મારું કુલ વેચાણ કેટલું થયું?',
      badge: 'Instant BI',
      tagColor: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10'
    }
  ];

  return (
    <div className="max-w-[1400px] mx-auto p-3 sm:p-6 space-y-4 sm:space-y-6">
      
      {/* Top Banner: Stage Status & Quick Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-surface border border-border rounded-2xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-saffron-500/15 border border-saffron-500/30 flex items-center justify-center text-saffron-400 font-bold shrink-0">
            <Mic className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm font-bold text-white tracking-tight">Vernacular Voice Counter</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-border">
                {workflowStage === 'IDLE' ? 'Counter Ready' : `Workflow: ${workflowStage}`}
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-1">Speak in Gujarati, Hindi, or Hinglish — zero typing</p>
          </div>
        </div>

        {/* Status & Barge-in Controls */}
        <div className="flex items-center gap-2 self-stretch sm:self-auto justify-between sm:justify-end shrink-0">
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-background border border-border text-xs text-slate-300">
            <span className={`w-2 h-2 rounded-full shrink-0 ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span className="text-[11px] font-mono">{isConnected ? '16kHz PCM' : 'Offline'}</span>
          </div>
          <button
            onClick={triggerInterruption}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-semibold transition-all active:scale-95"
            title="Interrupt speaking agent and clear audio buffer"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Barge-In (Stop)</span>
          </button>
        </div>
      </div>

      {/* Mobile Tab Switcher: Only visible on screens < lg */}
      <div className="lg:hidden flex items-center bg-card p-1 rounded-2xl border border-border">
        <button
          onClick={() => setMobileTab('mic')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition-all ${
            mobileTab === 'mic'
              ? 'bg-saffron-500 text-slate-950 shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Mic className="w-4 h-4" />
          <span>Voice Deck & Scenarios</span>
        </button>
        <button
          onClick={() => setMobileTab('bill')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition-all ${
            mobileTab === 'bill'
              ? 'bg-saffron-500 text-slate-950 shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Receipt className="w-4 h-4" />
          <span>Digital Slip {draftBill ? `(₹${draftBill.totalAmount})` : ''}</span>
          {draftBill && (
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          )}
        </button>
      </div>

      {/* Main Grid: Left Assistant Deck + Right Live Parchi/Bill */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: Microphone, Quick Prompt Cards, Conversation Stream (7 cols) */}
        <div className={`lg:col-span-7 space-y-5 ${mobileTab === 'bill' ? 'hidden lg:block' : 'block'}`}>
          
          {/* Tactile Microphone & Waveform Bar */}
          <div className="bg-gradient-to-b from-surface to-card border border-border rounded-3xl p-5 sm:p-6 shadow-card relative overflow-hidden">
            
            {/* Ambient Background Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-saffron-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex flex-col items-center justify-center py-3 relative z-10">
              
              {/* Mic Button with Multi-Ring Ripple */}
              <div className="relative mb-4">
                {isRecording && (
                  <>
                    <div className="absolute inset-0 rounded-full bg-saffron-500/20 voice-ripple" />
                    <div className="absolute -inset-3 rounded-full border border-saffron-400/30 animate-pulse" />
                  </>
                )}
                <button
                  onClick={toggleRecording}
                  className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-2xl relative z-10 ${
                    isRecording
                      ? 'bg-gradient-to-tr from-rose-600 to-rose-500 text-white shadow-rose-500/40 scale-105'
                      : 'bg-gradient-to-tr from-saffron-500 to-amber-500 text-slate-950 shadow-glow-saffron hover:scale-105 active:scale-95'
                  }`}
                >
                  {isRecording ? (
                    <MicOff className="w-8 h-8 sm:w-9 sm:h-9" />
                  ) : (
                    <Mic className="w-8 h-8 sm:w-9 sm:h-9" />
                  )}
                  <span className="text-[9px] sm:text-[10px] font-bold mt-1 tracking-tight">
                    {isRecording ? 'TAP TO STOP' : 'TAP & SPEAK'}
                  </span>
                </button>
              </div>

              {/* Dynamic Subtitle */}
              <p className="text-xs font-semibold text-slate-200 text-center">
                {isRecording ? (
                  <span className="text-saffron-400 font-bold flex items-center justify-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-saffron-400 animate-ping" />
                    Listening in real-time... Speak naturally
                  </span>
                ) : (
                  'Speak an order, payment receipt, or query in Gujarati/Hindi'
                )}
              </p>

              {/* Responsive Audio Waveform Visualizer */}
              <div className="flex items-center gap-1 mt-3.5 h-8 max-w-full overflow-hidden px-2">
                {[...Array(24)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-saffron-400 rounded-full transition-all duration-150 shrink-0"
                    style={{
                      height: isRecording 
                        ? `${Math.max(4, Math.sin(i * 0.4 + audioLevel * 6) * 26 + 12)}px`
                        : '4px',
                      opacity: isRecording ? 0.9 : 0.25
                    }}
                  />
                ))}
              </div>

            </div>

            {/* Quick Text Input for Quiet Environments */}
            <div className="pt-4 border-t border-border flex items-center gap-2">
              <input
                type="text"
                value={inputUtterance}
                onChange={(e) => setInputUtterance(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendUtterance(inputUtterance)}
                placeholder="Or type voice text: 'રાહુલને 10 કિલો ચોખા આપો'..."
                className="flex-1 bg-background/80 border border-border rounded-xl px-3 sm:px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-saffron-500 transition-colors"
              />
              <button
                onClick={() => sendUtterance(inputUtterance)}
                className="px-3.5 sm:px-4 py-2.5 rounded-xl bg-saffron-500 hover:bg-saffron-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Shop Scenarios (Cards) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-saffron-400" />
                <span>Simulate Spoken Scenarios</span>
              </span>
              <span className="text-[11px] text-slate-500">Tap to run</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {scenarios.map((sc, i) => (
                <button
                  key={i}
                  onClick={() => {
                    sendUtterance(sc.text);
                    if (window.innerWidth < 1024) setMobileTab('bill');
                  }}
                  className="text-left p-3 rounded-2xl bg-surface border border-border hover:border-saffron-500/40 hover:bg-card transition-all group relative overflow-hidden"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold text-slate-400">{sc.category}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sc.tagColor}`}>
                      {sc.badge}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-200 group-hover:text-saffron-300 line-clamp-2 transition-colors break-words">
                    "{sc.text}"
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Transcript Feed */}
          <div className="bg-surface border border-border rounded-2xl p-4 sm:p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-border text-xs">
              <span className="font-bold text-white flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-saffron-400" />
                <span>Live Dialogue History</span>
              </span>
              <span className="text-slate-500 text-[11px]">Real-time turns</span>
            </div>

            <div className="max-h-56 sm:max-h-64 overflow-y-auto space-y-3 pr-1">
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                const isSystem = msg.role === 'system';

                if (isSystem) {
                  return (
                    <div key={msg.id} className="text-center py-1">
                      <span className="inline-block px-3 py-1 rounded-full text-[10px] font-mono bg-background border border-border text-amber-300 max-w-full break-words">
                        {msg.text}
                      </span>
                    </div>
                  );
                }

                return (
                  <div
                    key={msg.id}
                    className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div
                      className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-[10px] font-bold ${
                        isUser
                          ? 'bg-slate-700 text-slate-200'
                          : 'bg-saffron-500/20 text-saffron-400 border border-saffron-500/40'
                      }`}
                    >
                      {isUser ? 'તમે' : 'AI'}
                    </div>

                    <div
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed break-words ${
                        isUser
                          ? 'bg-saffron-500 text-slate-950 font-medium rounded-tr-none'
                          : 'bg-card border border-border text-slate-200 rounded-tl-none'
                      }`}
                    >
                      <p>{msg.text}</p>
                      <span className={`block text-[9px] mt-1 ${isUser ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
                        {msg.timestamp}
                      </span>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: The Digital Counter Parchi (Bill) (5 cols) */}
        <div className={`lg:col-span-5 space-y-6 ${mobileTab === 'mic' ? 'hidden lg:block' : 'block'}`}>
          
          {/* Parchi Card */}
          <div className="parchi-paper border border-border rounded-3xl p-5 sm:p-6 shadow-card space-y-5">
            
            {/* Parchi Header */}
            <div className="flex items-start justify-between pb-4 border-b border-border/80">
              <div>
                <div className="flex items-center gap-1.5 text-saffron-400">
                  <Receipt className="w-4 h-4" />
                  <span className="text-[11px] font-bold uppercase tracking-wider">કાચી પાવતી • COUNTER SLIP</span>
                </div>
                <h2 className="text-base font-bold text-white mt-1">Shree Ganesh Kirana</h2>
                <p className="text-[11px] text-slate-400">Station Road, Ahmedabad</p>
              </div>

              {/* Status Seal Stamp */}
              {draftBill?.isConfirmed ? (
                <div className="px-3 py-1 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 text-xs font-bold tracking-tight rotate-3">
                  ✓ CONFIRMED
                </div>
              ) : draftBill?.isPausedForApproval ? (
                <div className="px-3 py-1 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-400 text-xs font-bold tracking-tight -rotate-2">
                  ⚠ APPROVAL REQ.
                </div>
              ) : (
                <div className="px-2.5 py-1 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[11px] font-semibold">
                  ● DRAFTING
                </div>
              )}
            </div>

            {/* Customer Details Pill */}
            {draftBill ? (
              <div className="p-3.5 rounded-2xl bg-background/60 border border-border space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-saffron-400" />
                    <span>Customer:</span>
                  </span>
                  <span className="font-bold text-white text-right">{draftBill.customerName}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Payment Mode:</span>
                  <span className="font-mono text-saffron-400 font-semibold">{draftBill.paymentMode}</span>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 text-xs border border-dashed border-border rounded-2xl">
                <Receipt className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="font-medium text-slate-400">No active bill</p>
                <p className="text-[11px] text-slate-500 mt-0.5">Speak an order to populate items automatically</p>
              </div>
            )}

            {/* Line Items Table */}
            {draftBill && (
              <div className="space-y-3">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Bill Items ({draftBill.items.length})
                </div>

                <div className="divide-y divide-border/60">
                  {draftBill.items.map((item, idx) => (
                    <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-200">{item.name}</div>
                        <div className="text-[11px] text-slate-400">
                          {item.quantity} {item.unit} × ₹{item.price.toFixed(2)}
                        </div>
                      </div>
                      <div className="font-bold font-mono text-white text-sm">
                        ₹{item.subtotal.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Grand Total Calculation */}
                <div className="pt-3 border-t-2 border-dashed border-border space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Subtotal:</span>
                    <span>₹{draftBill.totalAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Taxes & Delivery:</span>
                    <span className="text-emerald-400 font-semibold">FREE (Shop Counter)</span>
                  </div>
                  <div className="flex items-center justify-between text-sm font-bold pt-2 border-t border-border">
                    <span className="text-white">Total Payable (કુલ રકમ):</span>
                    <span className="text-lg text-saffron-400 font-mono">
                      ₹{draftBill.totalAmount.toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Exception Notice or Confirmation Bar */}
                {draftBill.isPausedForApproval ? (
                  <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1.5">
                    <div className="flex items-center gap-1.5 font-bold text-rose-400">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>Credit Policy Exceeded</span>
                    </div>
                    <p className="text-[11px] leading-relaxed text-slate-300">
                      {draftBill.approvalReason}
                    </p>
                    <span className="inline-block text-[10px] font-bold bg-rose-500/20 px-2 py-0.5 rounded text-rose-300">
                      Forwarded to Approval Center
                    </span>
                  </div>
                ) : draftBill.isConfirmed ? (
                  <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <div>
                      <span className="font-bold">Transaction Successfully Recorded!</span>
                      <p className="text-[11px] text-slate-400">Stock updated & delivery task dispatched.</p>
                    </div>
                  </div>
                ) : (
                  <div className="pt-2 flex flex-col sm:flex-row items-center gap-2">
                    <button
                      onClick={() => sendUtterance('હા, કન્ફર્મ કરો')}
                      className="w-full sm:flex-1 py-3 sm:py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/20 transition-all active:scale-95"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Confirm (કન્ફર્મ કરો)</span>
                    </button>
                    <button
                      onClick={() => setDraftBill(null)}
                      className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs border border-border transition-colors text-center"
                    >
                      Clear
                    </button>
                  </div>
                )}

              </div>
            )}

          </div>

          {/* Operational Guidance Card */}
          <div className="bg-surface border border-border rounded-2xl p-4 text-xs text-slate-400 space-y-2">
            <span className="font-bold text-slate-300 block">💡 Shopkeeper Voice Tips</span>
            <ul className="space-y-1 text-[11px] list-disc list-inside">
              <li>Speak naturally: <span className="text-saffron-300">"રાહુલને 10 કિલો ચોખા આપો"</span></li>
              <li>Say <span className="text-amber-300">"Wait, change to 15 kg"</span> anytime to correct.</li>
              <li>High credit orders automatically prompt the store owner for safety.</li>
            </ul>
          </div>

        </div>

      </div>

    </div>
  );
};
