import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="w-full sticky top-0 z-50 bg-white/30 backdrop-blur-2xl border-b border-white/40 shadow-[0_4px_30px_rgba(0,0,0,0.03)]">
      <div className="bg-primary/95 backdrop-blur-md text-white text-center py-2 px-4 text-sm tracking-wide">
        <a href="https://www.vezadigital.com/" className="hover:underline flex items-center justify-center gap-2">
          Explore Veza Digital Services <span aria-hidden="true">&rarr;</span>
        </a>
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col md:flex-row items-center justify-between">
        <div className="flex flex-col">
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-text-primary mb-0.5 drop-shadow-sm">
            WAIO <span className="text-primary font-bold">Webflow</span> Audit
          </h1>
          <p className="text-text-muted text-xs md:text-sm">Comprehensive checks for semantics, schema, CSS/JS, and WCAG.</p>
        </div>
        <div className="mt-3 md:mt-0 font-bold text-lg tracking-tighter drop-shadow-sm">
          VEZA<span className="text-primary">DIGITAL</span>
        </div>
      </div>
    </header>
  );
};
