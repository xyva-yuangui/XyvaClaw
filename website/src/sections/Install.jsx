import React, { useState } from 'react';
import { Copy, Check, Terminal, Monitor, Server } from 'lucide-react';
import { useLang, t } from '../i18n';

export default function Install() {
  const { lang } = useLang();
  const [tab, setTab] = useState('mac');
  const [mode, setMode] = useState('interactive');
  const [copied, setCopied] = useState(false);

  const commands = {
    mac: mode === 'auto'
      ? `DEEPSEEK_API_KEY=sk-your-key \\
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'`
      : `git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw
bash xyvaclaw-setup.sh`,
    linux: mode === 'auto'
      ? `DEEPSEEK_API_KEY=sk-your-key \\
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'`
      : `git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw
bash xyvaclaw-setup-linux.sh`,
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(commands[tab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const steps = mode === 'auto' ? [
    { icon: '✅', en: 'Auto-install all dependencies (Node.js, Python, ffmpeg)', zh: '自动安装所有依赖（Node.js、Python、ffmpeg）' },
    { icon: '📦', en: 'Install OpenClaw runtime', zh: '安装 OpenClaw 运行时' },
    { icon: '🔑', en: 'Inject API keys from environment variables', zh: '从环境变量注入 API Key' },
    { icon: '🚀', en: 'Deploy configs, skills (38+), extensions', zh: '部署配置、技能（38+）、扩展' },
    { icon: '⚙️', en: 'Register system service + auto-start gateway', zh: '注册系统服务 + 自动启动 Gateway' },
    { icon: '🎉', en: 'Done! Zero interaction required', zh: '完成！全程零交互' },
  ] : [
    { icon: '✅', en: 'Check & install dependencies (Node.js 22+, Python 3, ffmpeg)', zh: '检测并安装依赖（Node.js 22+、Python 3、ffmpeg）' },
    { icon: '📦', en: 'Install OpenClaw runtime via npm', zh: '通过 npm 安装 OpenClaw 运行时' },
    { icon: '🌐', en: 'Launch Web Setup Wizard — configure API keys in browser', zh: '启动 Web 配置向导 — 在浏览器中配置 API Key' },
    { icon: '🚀', en: 'Deploy configs, skills (38+), and extensions', zh: '部署配置、技能（38+）和扩展' },
    { icon: '🔧', en: 'Generate identity files from templates', zh: '从模板生成身份文件' },
    { icon: '⚙️', en: 'Register system service — auto-start on boot', zh: '注册系统服务 — 开机自启' },
  ];

  return (
    <section id="install" className="py-24 px-6 relative">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            <span className="gradient-text">{t(lang, '两分钟', 'Two minutes')}</span> {t(lang, '完成部署。', 'to launch.')}
          </h2>
          <p className="text-gray-400 text-lg">
            {t(lang, '一条命令部署，浏览器中完成配置', 'One command to deploy, configure in browser')}
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex justify-center gap-3 mb-4">
          <button
            onClick={() => setMode('interactive')}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition ${mode === 'interactive' ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}
          >
            {t(lang, '🌐 交互式安装', '🌐 Interactive')}
          </button>
          <button
            onClick={() => setMode('auto')}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition ${mode === 'auto' ? 'bg-brand-600/20 text-brand-400 ring-1 ring-brand-500/30' : 'text-gray-500 hover:text-gray-300'}`}
          >
            {t(lang, '⚡ 一键无人值守', '⚡ One-Liner Auto')}
          </button>
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
            {t(lang, '安装器自动完成以下步骤：', 'The installer handles everything:')}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {steps.map((step, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5"
              >
                <span className="text-lg mt-0.5">{step.icon}</span>
                <span className="text-sm text-gray-400">{t(lang, step.zh, step.en)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Requirements */}
        <div className="mt-10 text-center">
          <p className="text-sm text-gray-500">
            <strong className="text-gray-400">{t(lang, '环境要求：', 'Requirements: ')}</strong>
            Node.js 22+ · Python 3.10+ · {t(lang, '至少一个 API Key（', 'At least one API key (')}
            <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300">DeepSeek</a>{' '}
            {t(lang, '或', 'or')}{' '}
            <a href="https://bailian.console.aliyun.com/" target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300">{t(lang, '百炼', 'Bailian')}</a>
            )
          </p>
          {mode === 'auto' && (
            <p className="text-xs text-gray-600 mt-2">
              {t(lang,
                '💡 小窍门：缺少依赖也不用担心，--auto 模式会自动安装 Node.js、Python、ffmpeg。只需提前准备好 API Key 即可。',
                '💡 Tip: Even if you have nothing installed, --auto mode handles everything. Just have your API key ready.'
              )}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
