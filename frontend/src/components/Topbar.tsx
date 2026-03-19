import React from 'react';
import { Bell, Search, User, Activity } from 'lucide-react';

export const Topbar: React.FC = () => {
  return (
    <header className="h-20 border-b border-white/40 px-6 md:px-8 flex items-center justify-between bg-white/30 backdrop-blur-xl sticky top-0 z-10 shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
      <div className="md:hidden font-bold text-xl tracking-tighter text-text-primary drop-shadow-sm flex items-center gap-1">
        <Activity className="text-primary" size={24} />
        VEZA<span className="text-primary">DIGITAL</span>
      </div>

      <div className="hidden md:block relative w-96">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
        <input 
          type="text" 
          placeholder="Search audits..." 
          className="w-full pl-12 pr-4 py-2.5 bg-white/50 backdrop-blur-md border border-white/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/40 focus:bg-white/70 transition-all text-sm font-semibold text-text-body placeholder-gray-500 shadow-sm"
        />
      </div>
      
      <div className="flex items-center gap-4">
        <button className="w-10 h-10 flex items-center justify-center bg-white/60 backdrop-blur-md border border-white/80 shadow-sm rounded-xl hover:bg-white/80 transition-all text-gray-600">
          <Bell size={18} />
        </button>
        <div className="flex items-center gap-3 pl-4 border-l border-white/40 cursor-pointer">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-bold text-text-primary leading-tight">Admin User</div>
            <div className="text-xs font-semibold text-text-muted">SEO Specialist</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary border border-primary/20 shadow-sm">
            <User size={18} fill="currentColor" />
          </div>
        </div>
      </div>
    </header>
  );
};
