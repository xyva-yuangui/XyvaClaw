import React, { useState } from 'react';
import { Copy, Check, Terminal, Monitor, Server } from 'lucide-react';

export default function Install() {
  const [tab, setTab] = useState('mac');
  const [copied, setCopied] = useState(false);

  const commands = {
    mac: `git clone https://github.com/YOUR_USERNAME/xyvaclaw.git
cd xyvaclaw
bash xyvaclaw-setup.sh`,
    linux: `git clone https://github.com/YOUR_USERNAME/xyvaclaw.git
cd xyvaclaw
bash xyvaclaw-setup-linux.sh`,
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(commands[tab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const steps = [
    { icon: '✅', text: 'Check & install dependencies (Node.js 22+, Python 3, ffmpeg)' },
    { icon: '📦', text: 'Install OpenClaw runtime via npm' },
    { icon: '🌐', text: 'Launch Web Setup Wizard — configure API keys in browser' },
    { icon: '🚀', text: 'Deploy configs, skills (38), and extensions (Feishu + Lossless-Claw)' },
    { icon: '🔧', text: 'Generate identity files from templates' },
    { icon: '⚙️', text: 'Register system service — auto-start on boot' },
  ];

  return (
    <section id="install" className="py-24 px-6 relative">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            <span className="gradient-text">Two minutes</span> to launch.
          </h2>
          <p className="text-gray-400 text-lg">
            两分钟完成部署，浏览器中完成配置
          </p>
        </div>

        {/* OS Tabs */}
        <div className="flex justify-center gap-3 mb-6">
          <button
            onClick={() => setTab('mac')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition ${
              tab === 'mac'
                ? 'bg-brand-600 text-white'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <Monitor size={16} />
            macOS
          </button>
          <button
            onClick={() => setTab('linux')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition ${
              tab === 'linux'
                ? 'bg-brand-600 text-white'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            <Server size={16} />
            Linux
          </button>
        </div>

        {/* Terminal */}
        <div className="rounded-2xl border border-white/10 bg-gray-900/80 overflow-hidden glow-blue">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/[0.02]">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <span className="text-xs text-gray-500 ml-2 font-mono">
                <Terminal size={12} className="inline mr-1" />
                {tab === 'mac' ? 'Terminal — zsh' : 'Terminal — bash'}
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="text-gray-500 hover:text-brand-400 transition"
            >
              {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
            </button>
          </div>
          <div className="p-6 font-mono text-sm leading-relaxed">
            {commands[tab].split('\n').map((line, i) => (
              <div key={i} className="flex">
                <span className="text-brand-400 mr-3 select-none">$</span>
                <span className="text-gray-300">{line}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Steps */}
        <div className="mt-12">
          <h3 className="text-lg font-semibold text-gray-300 mb-6 text-center">
            The installer handles everything:
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {steps.map((step, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5"
              >
                <span className="text-lg mt-0.5">{step.icon}</span>
                <span className="text-sm text-gray-400">{step.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Requirements */}
        <div className="mt-10 text-center">
          <p className="text-sm text-gray-500">
            <strong className="text-gray-400">Requirements:</strong>{' '}
            Node.js 22+ · Python 3.10+ · At least one API key (
            <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300">DeepSeek</a>{' '}
            or{' '}
            <a href="https://bailian.console.aliyun.com/" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300">Bailian</a>
            )
          </p>
        </div>
      </div>
    </section>
  );
}
