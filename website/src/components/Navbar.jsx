import React, { useState, useEffect } from 'react';
import { Github, Menu, X, Globe } from 'lucide-react';
import { useLang, t } from '../i18n';

const LINKS = [
  { en: 'Features', zh: '特性', href: '#features' },
  { en: 'Comparison', zh: '对比', href: '#comparison' },
  { en: 'Skills', zh: '技能', href: '#skills' },
  { en: 'Install', zh: '安装', href: '#install' },
  { en: 'Architecture', zh: '架构', href: '#docs' },
];

export default function Navbar() {
  const { lang, toggle } = useLang();
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
        <a href="#" className="flex items-center group">
          <img src="./logo.png" alt="xyvaClaw" className="h-8 w-auto" />
        </a>

        <div className="hidden md:flex items-center gap-8">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-gray-400 hover:text-white transition"
            >
              {t(lang, l.zh, l.en)}
            </a>
          ))}

          <button
            onClick={toggle}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-gray-400 hover:bg-white/10 hover:text-white transition"
            title={t(lang, 'Switch to English', '切换到中文')}
          >
            <Globe size={14} />
            {lang === 'zh' ? 'EN' : '中文'}
          </button>

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

        <div className="flex items-center gap-3 md:hidden">
          <button
            onClick={toggle}
            className="text-sm text-gray-400 hover:text-white px-2 py-1 rounded bg-white/5"
          >
            {lang === 'zh' ? 'EN' : '中文'}
          </button>
          <button
            onClick={() => setOpen(!open)}
            className="text-gray-400 hover:text-white"
          >
            {open ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
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
              {t(lang, l.zh, l.en)}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
}
