import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-surface-raised border-t border-border py-12 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex flex-col text-center md:text-left">
          <div className="font-bold text-2xl tracking-tighter text-text mb-2">
            VEZA<span className="text-accent">DIGITAL</span>
          </div>
          <p className="text-sm text-text-muted">&copy; {new Date().getFullYear()} Veza Digital. All rights reserved.</p>
        </div>
        <div className="flex gap-6 text-sm text-text-secondary">
           <a href="https://www.vezadigital.com/privacy" className="hover:text-text transition-colors">Privacy Policy</a>
           <a href="https://www.vezadigital.com/terms" className="hover:text-text transition-colors">Terms of Service</a>
        </div>
      </div>
    </footer>
  );
};
