import React from 'react';
import { Github, FileText, MessageSquare, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-white/5 bg-gray-950">
      {/* CTA Banner */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl sm:text-4xl font-bold mb-4">
          Ready to meet your{' '}
          <span className="gradient-text">AI partner</span>?
        </h2>
        <p className="text-gray-400 text-lg mb-8">
          两分钟部署，从此拥有一个越用越懂你的 AI 伙伴
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw"
            className="group flex items-center gap-2 px-8 py-3.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-semibold text-lg transition shadow-lg shadow-brand-600/25"
          >
            <Github size={20} />
            Clone from GitHub
          </a>
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw/releases"
            className="flex items-center gap-2 px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white rounded-xl font-medium text-lg transition"
          >
            Download Release
          </a>
        </div>
      </div>

      {/* Links */}
      <div className="max-w-7xl mx-auto px-6 pb-12 grid grid-cols-2 sm:grid-cols-4 gap-8 text-sm">
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">Product</h4>
          <ul className="space-y-2">
            <li><a href="#features" className="text-gray-500 hover:text-gray-300 transition">Features</a></li>
            <li><a href="#comparison" className="text-gray-500 hover:text-gray-300 transition">Comparison</a></li>
            <li><a href="#skills" className="text-gray-500 hover:text-gray-300 transition">Skills</a></li>
            <li><a href="#install" className="text-gray-500 hover:text-gray-300 transition">Install</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">Documentation</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/API-KEYS-GUIDE.md" className="text-gray-500 hover:text-gray-300 transition">API Keys Guide</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FEISHU-SETUP.md" className="text-gray-500 hover:text-gray-300 transition">Feishu Setup</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FAQ.md" className="text-gray-500 hover:text-gray-300 transition">FAQ</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/PRODUCT-INTRODUCTION.md" className="text-gray-500 hover:text-gray-300 transition">Product Intro</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">Community</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw" className="text-gray-500 hover:text-gray-300 transition">GitHub</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/issues" className="text-gray-500 hover:text-gray-300 transition">Issues</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/discussions" className="text-gray-500 hover:text-gray-300 transition">Discussions</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">Powered By</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/nicepkg/openclaw" className="text-gray-500 hover:text-gray-300 transition">OpenClaw</a></li>
            <li><a href="https://platform.deepseek.com/" className="text-gray-500 hover:text-gray-300 transition">DeepSeek</a></li>
            <li><a href="https://bailian.console.aliyun.com/" className="text-gray-500 hover:text-gray-300 transition">Bailian</a></li>
          </ul>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/5 py-6 px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>🐾</span>
            <span>
              <strong className="text-gray-500">xyvaClaw</strong> — From Claw to xyvaClaw, not a replacement, but an evolution.
            </span>
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-600">
            Made with <Heart size={14} className="text-red-500/60 mx-0.5" /> · MIT License · {new Date().getFullYear()}
          </div>
        </div>
      </div>
    </footer>
  );
}
