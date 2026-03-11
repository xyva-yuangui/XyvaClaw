import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, ArrowRight, Star } from 'lucide-react';
import { useLang, t } from '../i18n';

export default function Hero() {
  const { lang } = useLang();
  const [copied, setCopied] = useState(false);
  const cmd = 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh';

  const handleCopy = () => {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="relative min-h-screen flex items-center justify-center aurora grid-bg overflow-hidden">
      <div className="absolute top-20 left-10 w-72 h-72 bg-brand-600/20 rounded-full blur-[100px] animate-float" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-500/10 rounded-full blur-[120px] animate-float-delay" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center pt-24 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-900/30 border border-brand-700/30 text-brand-300 text-sm mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          v1.0.0 — Powered by OpenClaw Runtime
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-5xl sm:text-6xl lg:text-8xl font-black tracking-tight leading-[1.1] mb-6"
        >
          <span className="gradient-text">
            {t(lang, '你的 AI', 'Your AI')}
          </span>
          <br />
          <span className="text-white">
            {t(lang, '会进化', 'That Evolves')}
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          <strong className="text-white">
            {t(lang, '38+ 技能。', '38+ skills.')}
          </strong>{' '}
          {t(lang, '自我进化引擎。五级模型容灾。飞书深度集成。', 'Self-evolution engine. 5-level model fallback. Deep Feishu integration.')}
          <br />
          <span className="text-brand-300">
            {t(lang, '一条命令部署，两分钟完成配置。', 'One command to deploy. Two minutes to configure.')}
          </span>
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="max-w-2xl mx-auto mb-10"
        >
          <div className="gradient-border">
            <div
              className="flex items-center justify-between bg-gray-900 rounded-[15px] px-5 py-3.5 cursor-pointer group"
              onClick={handleCopy}
            >
              <code className="text-sm sm:text-base text-gray-300 font-mono truncate pr-4">
                <span className="text-brand-400">$</span>{' '}
                git clone ... && bash xyvaclaw-setup.sh
              </code>
              <button className="flex-shrink-0 text-gray-500 group-hover:text-brand-400 transition">
                {copied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
              </button>
            </div>
          </div>
          {copied && (
            <p className="text-sm text-green-400 mt-2">
              {t(lang, '已复制到剪贴板！', 'Copied to clipboard!')}
            </p>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw"
            className="group flex items-center gap-2 px-8 py-3.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-semibold text-lg transition shadow-lg shadow-brand-600/25 hover:shadow-brand-500/40"
          >
            {t(lang, '立即开始', 'Get Started')}
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </a>
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw"
            className="group flex items-center gap-2 px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white rounded-xl font-medium text-lg transition"
          >
            <Star size={18} />
            Star on GitHub
          </a>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.8 }}
          className="mt-16 flex items-center justify-center gap-8 sm:gap-16"
        >
          {[
            { value: '38+', en: 'Skills', zh: '技能' },
            { value: '112', en: 'Feishu TS Files', zh: '飞书 TS 文件' },
            { value: '5', en: 'Fallback Levels', zh: '级容灾' },
            { value: '2 min', en: 'Setup Time', zh: '部署时间' },
          ].map((stat) => (
            <div key={stat.en} className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white">{stat.value}</div>
              <div className="text-xs sm:text-sm text-gray-500">{t(lang, stat.zh, stat.en)}</div>
            </div>
          ))}
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1 }}
          className="mt-8 text-sm text-gray-600"
        >
          {t(lang, '由', 'By')}{' '}
          <a href="https://github.com/xyva-yuangui" target="_blank" rel="noopener noreferrer" className="text-brand-400/70 hover:text-brand-300 transition">
            Xyva-yuangui（圆规）
          </a>{' '}
          {t(lang, '精心打造', 'crafted with passion')}
        </motion.p>
      </div>
    </section>
  );
}
