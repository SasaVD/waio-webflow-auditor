import React from 'react';
import { LayoutDashboard, CheckSquare, FileText, Settings, Activity } from 'lucide-react';

export const Sidebar: React.FC = () => {
  return (
    <aside className="hidden md:flex flex-col w-64 border-r border-white/40 p-6 bg-white/30 backdrop-blur-xl z-20 shadow-[10px_0_30px_rgba(0,0,0,0.02)]">
      <div className="mb-12 font-bold text-2xl tracking-tighter text-text-primary drop-shadow-sm flex items-center gap-2">
        <Activity className="text-primary" size={28} />
        VEZA<span className="text-primary">DIGITAL</span>
      </div>
      
      <nav className="flex-1 space-y-2">
        <div className="text-xs font-bold text-text-muted uppercase tracking-widest mb-4 ml-2">Main Menu</div>
        
        <a href="#" className="flex items-center gap-3 px-4 py-3.5 rounded-xl bg-white/70 text-primary font-bold shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-white transition-all hover:-translate-y-0.5">
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </a>
        
        <a href="#" className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-text-muted font-semibold hover:bg-white/50 hover:text-text-primary transition-all">
          <CheckSquare size={20} />
          <span>Audits</span>
        </a>
        
        <a href="#" className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-text-muted font-semibold hover:bg-white/50 hover:text-text-primary transition-all">
          <FileText size={20} />
          <span>Reports</span>
        </a>
      </nav>
      
      <div className="mt-auto pt-6 border-t border-white/40">
        <a href="#" className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-text-muted font-semibold hover:bg-white/50 hover:text-text-primary transition-all">
          <Settings size={20} />
          <span>Settings</span>
        </a>
      </div>
    </aside>
  );
};
