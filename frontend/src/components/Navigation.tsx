import React from 'react';
import { 
  Mic, LayoutDashboard, ShoppingBag, Package, Users, ShieldAlert, BarChart3, Store, Globe, Sparkles
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
    { id: 'voice', label: 'Voice Counter', icon: Mic, isHero: true },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'orders', label: 'Orders', icon: ShoppingBag },
    { id: 'inventory', label: 'Inventory', icon: Package },
    { id: 'customers', label: 'Khata Ledger', icon: Users },
    { 
      id: 'approvals', 
      label: 'Approvals', 
      icon: ShieldAlert, 
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : null 
    },
    { id: 'analytics', label: 'Impact & ROI', icon: BarChart3 },
  ];

  return (
    <>
      {/* Desktop & Tablet Top Navigation Bar */}
      <header className="border-b border-border/80 bg-surface/95 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
          
          {/* Brand Identity */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-saffron-500 to-amber-600 flex items-center justify-center shadow-glow-saffron text-slate-950 font-black">
              <Store className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-sm sm:text-base tracking-tight text-white">VyaparVaani</span>
                <span className="hidden sm:inline-block text-[10px] font-bold px-2 py-0.5 rounded-full bg-saffron-500/15 text-saffron-400 border border-saffron-500/30 tracking-wide uppercase">
                  AI Voice POS
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-slate-400 font-medium truncate max-w-[140px] sm:max-w-none">
                Shree Ganesh Kirana • Ahmedabad
              </p>
            </div>
          </div>

          {/* Central Tabs: Visible on Large Screens */}
          <nav className="hidden lg:flex items-center gap-1 bg-background/80 p-1.5 rounded-2xl border border-border">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? item.isHero
                        ? 'bg-gradient-to-r from-saffron-500 to-amber-500 text-slate-950 shadow-glow-saffron font-bold'
                        : 'bg-card text-white border border-border-strong shadow-sm'
                      : item.isHero
                      ? 'text-saffron-400 hover:bg-saffron-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive && item.isHero ? 'text-slate-950' : ''}`} />
                  <span>{item.label}</span>
                  {item.badge !== null && (
                    <span className="w-4 h-4 rounded-full bg-danger text-white text-[10px] font-black flex items-center justify-center animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Controls: Vernacular Selector & Gemini Live Status */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            
            {/* Language Selector */}
            <div className="flex items-center bg-card border border-border rounded-xl p-1 shadow-sm">
              <Globe className="w-3.5 h-3.5 text-saffron-400 ml-1.5 sm:ml-2 shrink-0" />
              <select
                value={currentLanguage}
                onChange={(e) => setCurrentLanguage(e.target.value)}
                className="bg-transparent text-[11px] sm:text-xs font-semibold text-slate-200 pl-1 pr-2 sm:pr-3 py-1 focus:outline-none cursor-pointer max-w-[110px] sm:max-w-none"
              >
                <option value="gu-IN" className="bg-surface text-slate-100">🇮🇳 ગુજરાતી</option>
                <option value="hi-IN" className="bg-surface text-slate-100">🇮🇳 हिन्दी</option>
                <option value="hinglish" className="bg-surface text-slate-100">🇮🇳 Hinglish</option>
                <option value="en-IN" className="bg-surface text-slate-100">🌐 English</option>
              </select>
            </div>

            {/* Gemini Live connection indicator */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono text-[11px] tracking-tight">Gemini Live</span>
            </div>

          </div>

        </div>

        {/* Tablet Horizontal Scroll Tab Bar (md to lg) */}
        <div className="hidden md:flex lg:hidden items-center gap-1 overflow-x-auto px-4 py-2 border-t border-border bg-surface">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs whitespace-nowrap font-medium transition-colors ${
                  isActive ? 'bg-saffron-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
                {item.badge !== null && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-danger text-white font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* Mobile Bottom Fixed Dock (Phones & Small Tablets) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface/95 backdrop-blur-xl border-t border-border px-3 py-2 flex items-center justify-around shadow-2xl">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center justify-center gap-1 py-1 px-2 rounded-xl transition-all relative ${
                isActive ? 'text-saffron-400 font-bold' : 'text-slate-400'
              }`}
            >
              {item.isHero ? (
                <div className={`w-10 h-10 -mt-5 rounded-full flex items-center justify-center shadow-glow-saffron ${
                  isActive ? 'bg-saffron-500 text-slate-950' : 'bg-card border border-saffron-500/40 text-saffron-400'
                }`}>
                  <Icon className="w-5 h-5" />
                </div>
              ) : (
                <Icon className="w-4 h-4" />
              )}
              <span className="text-[10px] tracking-tight">{item.label.split(' ')[0]}</span>
              {item.badge !== null && (
                <span className="absolute top-0 right-1 w-3.5 h-3.5 rounded-full bg-danger text-white text-[9px] font-black flex items-center justify-center">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </>
  );
};
