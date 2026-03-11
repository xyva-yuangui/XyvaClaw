import React, { useState, useEffect } from 'react';
import { Github, Menu, X } from 'lucide-react';

const LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Comparison', href: '#comparison' },
  { label: 'Skills', href: '#skills' },
  { label: 'Install', href: '#install' },
  { label: 'Docs', href: '#docs' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-gray-950/80 backdrop-blur-xl border-b border-white/5'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2 group">
          <span className="text-2xl">🐾</span>
          <span className="text-lg font-bold">
            <span className="text-brand-400 group-hover:text-brand-300 transition">xyva</span>
            <span className="text-white">Claw</span>
          </span>
        </a>

        <div className="hidden md:flex items-center gap-8">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-gray-400 hover:text-white transition"
            >
              {l.label}
            </a>
          ))}
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-gray-300 hover:bg-white/10 hover:text-white transition"
          >
            <Github size={16} />
            GitHub
          </a>
        </div>

        <button
          onClick={() => setOpen(!open)}
          className="md:hidden text-gray-400 hover:text-white"
        >
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {open && (
        <div className="md:hidden bg-gray-950/95 backdrop-blur-xl border-b border-white/5 px-6 pb-4 space-y-3">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block text-gray-400 hover:text-white py-1"
            >
              {l.label}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
}
