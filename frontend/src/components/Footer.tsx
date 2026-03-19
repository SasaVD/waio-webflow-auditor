import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-bg-dark text-text-on-dark py-12 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex flex-col text-center md:text-left">
          <div className="font-bold text-2xl tracking-tighter mb-2">
            VEZA<span className="text-primary">DIGITAL</span>
          </div>
          <p className="text-sm text-gray-400">© {new Date().getFullYear()} Veza Digital. All rights reserved.</p>
        </div>
        <div className="flex gap-6 text-sm text-gray-300">
           <a href="https://www.vezadigital.com/privacy" className="hover:text-white transition-colors">Privacy Policy</a>
           <a href="https://www.vezadigital.com/terms" className="hover:text-white transition-colors">Terms of Service</a>
        </div>
      </div>
    </footer>
  );
};
