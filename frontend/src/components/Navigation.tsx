import React from 'react';
import { 
  Mic, LayoutDashboard, ShoppingCart, Package, Users, ShieldAlert, BarChart3, Radio
} from 'lucide-react';

interface NavigationProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingApprovalsCount: number;
  currentLanguage: string;
  setCurrentLanguage: (lang: string) => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  setActiveTab,
  pendingApprovalsCount,
  currentLanguage,
  setCurrentLanguage
}) => {
  const navItems = [
    { id: 'voice', label: 'Voice Command', icon: Mic, badge: null, highlight: true },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
    { id: 'orders', label: 'Orders', icon: ShoppingCart, badge: null },
    { id: 'inventory', label: 'Inventory', icon: Package, badge: null },
    { id: 'customers', label: 'Customers & Khata', icon: Users, badge: null },
    { id: 'approvals', label: 'Approval Center', icon: ShieldAlert, badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : null },
    { id: 'analytics', label: 'Agent Impact', icon: BarChart3, badge: null },
  ];

  return (
    <header className="border-b border-border bg-surface/90 backdrop-blur sticky top-0 z-50 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-primary flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">VyaparVaani AI</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary-glow font-medium border border-primary/30">
                Gemini Live v2.0
              </span>
            </div>
            <p className="text-xs text-slate-400">વેપારવાણી • Multilingual Agentic Operations</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 bg-card/60 p-1 rounded-xl border border-border">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-primary text-slate-950 font-semibold shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-slate-950' : item.highlight ? 'text-primary' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {item.badge !== null && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-warning text-slate-950 font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Vernacular Language Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Language:</span>
          <select
            value={currentLanguage}
            onChange={(e) => setCurrentLanguage(e.target.value)}
            className="bg-card text-xs text-slate-200 border border-border rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary"
          >
            <option value="gu-IN">ગુજરાતી (Gujarati)</option>
            <option value="hi-IN">हिन्दी (Hindi)</option>
            <option value="hinglish">Hinglish / Gujlish</option>
            <option value="en-IN">Indian English</option>
          </select>
        </div>

      </div>
    </header>
  );
};
