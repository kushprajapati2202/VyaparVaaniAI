import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Volume2, Sparkles, AlertTriangle, CheckCircle2, 
  ArrowRight, ShieldAlert, RefreshCw, Send, Zap, ChevronRight
} from 'lucide-react';
import { VoiceMessage } from '../../types';

interface VoiceCommandCenterProps {
  currentLanguage: string;
  onRefreshData?: () => void;
}

export const VoiceCommandCenter: React.FC<VoiceCommandCenterProps> = ({ currentLanguage, onRefreshData }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
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

  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Initialize WebSocket connection to FastAPI backend
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket('ws://localhost:8000/api/v1/voice/live');
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          const data = JSON.parse(event.data);
          handleServerEvent(data);
        } else if (event.data instanceof Blob) {
          // Received binary audio response from agent
          playAudioBlob(event.data);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (e) {
      console.warn('WebSocket connection error:', e);
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
      if (onRefreshData) onRefreshData();
    } else if (data.type === 'workflow_update') {
      setWorkflowStage(data.step);
    } else if (data.type === 'tool_executed') {
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: 'system',
          text: `Tool Executed: ${data.tool}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          toolCall: {
            tool: data.tool,
            args: data.args,
            result: data.result
          }
        }
      ]);
    } else if (data.type === 'approval_required') {
      setActiveApproval(data);
      setWorkflowStage('APPROVAL_PENDING');
      if (onRefreshData) onRefreshData();
    }
  };

  const playAudioBlob = async (blob: Blob) => {
    try {
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      await audio.play();
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  };

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Toggle Microphone
  const toggleRecording = () => {
    if (!isRecording) {
      setIsRecording(true);
      setWorkflowStage('LISTENING');
      // Simulate audio waveform animation
      simulateAudioWaveform();
    } else {
      setIsRecording(false);
      setWorkflowStage('PROCESSING');
      setAudioLevel(0);
    }
  };

  const simulateAudioWaveform = () => {
    const interval = setInterval(() => {
      setAudioLevel(Math.random() * 0.8 + 0.2);
    }, 150);
    setTimeout(() => {
      clearInterval(interval);
      if (isRecording) setAudioLevel(0.1);
    }, 4000);
  };

  // Send Utterance (Voice or Text fallback)
  const sendUtterance = (text: string) => {
    if (!text.trim()) return;
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'user_text', text }));
    } else {
      // Offline fallback display
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

  // User Interruption Trigger
  const triggerInterruption = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'user_interruption' }));
    }
    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(),
        role: 'system',
        text: '⚡ User interrupted agent response (Barge-in). Output buffer discarded.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const demoScenarios = [
    {
      title: 'Workflow 1: Gujarati Order',
      lang: 'ગુજરાતી',
      text: 'રાહુલને 10 કિલો ચોખા અને 5 કિલો ખાંડ આપવાના છે. આજે ડિલિવરી રાખજો.',
      badge: 'Order Intake',
      color: 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20'
    },
    {
      title: 'Workflow 2: Spoken Correction',
      lang: 'Barge-In',
      text: 'Wait, change rice quantity to 15 kg instead!',
      badge: 'Mid-Utterance',
      color: 'border-amber-500/40 text-amber-400 bg-amber-950/20'
    },
    {
      title: 'Workflow 3: Payment Record',
      lang: 'Hinglish',
      text: 'Rahul ka 2000 payment receive hua hai, uska ledger update kar do.',
      badge: 'Khata Update',
      color: 'border-emerald-500/40 text-emerald-400 bg-emerald-950/20'
    },
    {
      title: 'Workflow 4: Credit Risk & Approval',
      lang: 'Policy Check',
      text: 'Give Amit 50 kg rice on credit.',
      badge: 'Human-in-the-Loop',
      color: 'border-red-500/40 text-red-400 bg-red-950/20'
    },
    {
      title: 'Workflow 5: Conversational BI',
      lang: 'ગુજરાતી',
      text: 'આજનું મારું કુલ વેચાણ કેટલું થયું?',
      badge: 'Daily Sales',
      color: 'border-purple-500/40 text-purple-400 bg-purple-950/20'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* LEFT COLUMN: Microphone, Waveform, Quick Scenarios (5 cols) */}
      <div className="lg:col-span-5 space-y-6">
        
        {/* Voice Command Card */}
        <div className="bg-surface border border-border rounded-2xl p-6 relative overflow-hidden shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
              <span className="text-xs font-medium text-slate-300">
                {isConnected ? 'Gemini Live: Ready (16kHz PCM)' : 'Connecting to Voice Gateway...'}
              </span>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
              State: {workflowStage}
            </span>
          </div>

          {/* Central Microphone Waveform Ring */}
          <div className="py-6 flex flex-col items-center justify-center">
            <div className="relative">
              {isRecording && (
                <div 
                  className="absolute inset-0 rounded-full bg-primary/20 voice-glow" 
                  style={{ transform: `scale(${1 + audioLevel * 0.4})` }}
                />
              )}
              <button
                onClick={toggleRecording}
                className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 relative z-10 ${
                  isRecording
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/40 scale-105'
                    : 'bg-gradient-to-tr from-cyan-600 to-primary text-slate-950 shadow-lg shadow-cyan-500/30 hover:scale-105'
                }`}
              >
                {isRecording ? <MicOff className="w-10 h-10 animate-bounce" /> : <Mic className="w-10 h-10" />}
              </button>
            </div>

            <p className="mt-4 text-xs font-semibold text-slate-200">
              {isRecording ? 'Listening in real-time... Speak naturally' : 'Tap to Speak in Gujarati, Hindi or English'}
            </p>

            {/* Simulated Live Audio Waveform Bars */}
            <div className="flex items-center gap-1.5 mt-4 h-8">
              {[...Array(16)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-primary rounded-full transition-all duration-150"
                  style={{
                    height: isRecording 
                      ? `${Math.max(4, Math.sin(i * 0.5 + audioLevel * 5) * 28 + 14)}px`
                      : '4px',
                    opacity: isRecording ? 0.9 : 0.3
                  }}
                />
              ))}
            </div>

            {/* Barge-In Interruption Button */}
            <button
              onClick={triggerInterruption}
              className="mt-4 flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 bg-amber-950/30 border border-amber-800/40 px-3 py-1 rounded-lg transition-colors"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Simulate Mid-Sentence Interruption</span>
            </button>
          </div>

          {/* Text Utterance Input Bar */}
          <div className="mt-4 pt-4 border-t border-border flex items-center gap-2">
            <input
              type="text"
              value={inputUtterance}
              onChange={(e) => setInputUtterance(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendUtterance(inputUtterance)}
              placeholder="Or type voice instruction here..."
              className="flex-1 bg-card border border-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
            />
            <button
              onClick={() => sendUtterance(inputUtterance)}
              className="p-2 rounded-xl bg-primary text-slate-950 hover:bg-primary-hover font-semibold transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Hackathon Preset Scenarios */}
        <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Official Hackathon Demonstration Workflows
            </h3>
          </div>
          <p className="text-[11px] text-slate-400 mb-3">
            Click any workflow to send live vernacular input directly to the agent engine:
          </p>

          <div className="space-y-2">
            {demoScenarios.map((sc, i) => (
              <button
                key={i}
                onClick={() => sendUtterance(sc.text)}
                className="w-full text-left p-2.5 rounded-xl border border-border bg-card/60 hover:bg-card hover:border-slate-600 transition-all group flex items-start justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-primary transition-colors">
                      {sc.title}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full border ${sc.color}`}>
                      {sc.badge}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 font-sans line-clamp-1">"{sc.text}"</p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-primary transition-colors shrink-0 mt-1" />
              </button>
            ))}
          </div>
        </div>

      </div>

      {/* RIGHT COLUMN: Live Transcript & Agent Workflow Steps (7 cols) */}
      <div className="lg:col-span-7 space-y-6">
        
        {/* Conversation Transcript Feed */}
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl flex flex-col h-[620px]">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-bold text-white">Live Conversation Transcript</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Turn-taking: Native Audio Barge-in
            </span>
          </div>

          {/* Transcript Message Stream */}
          <div className="flex-1 overflow-y-auto space-y-4 py-4 pr-1">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isSystem = msg.role === 'system';

              if (isSystem) {
                return (
                  <div key={msg.id} className="text-center py-1">
                    <span className="inline-block px-3 py-1 rounded-full text-[11px] font-mono bg-slate-800/80 text-amber-300 border border-slate-700">
                      {msg.text}
                    </span>
                    {msg.toolCall && (
                      <div className="mt-1 max-w-md mx-auto text-left bg-slate-900 border border-slate-800 rounded-lg p-2 text-[10px] font-mono text-cyan-300">
                        <span className="text-slate-400">args:</span> {JSON.stringify(msg.toolCall.args)}
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <div
                  key={msg.id}
                  className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                      isUser
                        ? 'bg-slate-700 text-slate-200'
                        : 'bg-primary/20 text-primary-glow border border-primary/40'
                    }`}
                  >
                    {isUser ? 'U' : 'AI'}
                  </div>

                  <div
                    className={`max-w-[82%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                      isUser
                        ? 'bg-primary text-slate-950 font-medium rounded-tr-none'
                        : 'bg-card border border-border text-slate-200 rounded-tl-none shadow-sm'
                    }`}
                  >
                    <p className="text-[13px]">{msg.text}</p>
                    <span className={`block text-[10px] mt-1.5 ${isUser ? 'text-slate-800' : 'text-slate-500'}`}>
                      {msg.timestamp}
                    </span>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Active Approval Banner if required */}
          {activeApproval && (
            <div className="mt-3 p-3 rounded-xl bg-amber-950/40 border border-amber-600/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-amber-300">Supervisor Approval Required</p>
                  <p className="text-[11px] text-slate-300">{activeApproval.reason}</p>
                </div>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-amber-500 text-slate-950 font-bold shrink-0">
                Action Paused
              </span>
            </div>
          )}

        </div>

      </div>

    </div>
  );
};
