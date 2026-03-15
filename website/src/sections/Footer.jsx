import React from 'react';
import { Github, FileText, MessageSquare, Heart, Twitter } from 'lucide-react';
import { useLang, t } from '../i18n';

export default function Footer() {
  const { lang } = useLang();
  return (
    <footer className="border-t border-white/5 bg-gray-950">
      {/* CTA Banner */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl sm:text-4xl font-bold mb-4">
          {t(lang, '准备好迎接你的', 'Ready to meet your ')}{' '}
          <span className="gradient-text">{t(lang, 'AI 伙伴', 'AI partner')}</span>
          {t(lang, '了吗？', '?')}
        </h2>
        <p className="text-gray-400 text-lg mb-8">
          {t(lang, '两分钟部署，从此拥有一个越用越懂你的 AI 伙伴', 'Two minutes to deploy, then you have an AI partner that gets smarter every day')}
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw"
            className="group flex items-center gap-2 px-8 py-3.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-semibold text-lg transition shadow-lg shadow-brand-600/25"
          >
            <Github size={20} />
            {t(lang, '从 GitHub 获取', 'Clone from GitHub')}
          </a>
          <a
            href="https://github.com/xyva-yuangui/XyvaClaw/releases"
            className="flex items-center gap-2 px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white rounded-xl font-medium text-lg transition"
          >
            {t(lang, '下载 Release', 'Download Release')}
          </a>
        </div>
      </div>

      {/* Links */}
      <div className="max-w-7xl mx-auto px-6 pb-12 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 text-sm">
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">{t(lang, '产品', 'Product')}</h4>
          <ul className="space-y-2">
            <li><a href="#features" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '特性', 'Features')}</a></li>
            <li><a href="#comparison" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '对比', 'Comparison')}</a></li>
            <li><a href="#skills" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '技能', 'Skills')}</a></li>
            <li><a href="#install" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '安装', 'Install')}</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">{t(lang, '文档', 'Documentation')}</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/API-KEYS-GUIDE.md" className="text-gray-500 hover:text-gray-300 transition">{t(lang, 'API Key 指南', 'API Keys Guide')}</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FEISHU-SETUP.md" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '飞书配置', 'Feishu Setup')}</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FAQ.md" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '常见问题', 'FAQ')}</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/PRODUCT-INTRODUCTION.md" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '产品介绍', 'Product Intro')}</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">{t(lang, '社区', 'Community')}</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw" className="text-gray-500 hover:text-gray-300 transition">GitHub</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/issues" className="text-gray-500 hover:text-gray-300 transition">Issues</a></li>
            <li><a href="https://github.com/xyva-yuangui/XyvaClaw/discussions" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '讨论', 'Discussions')}</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">{t(lang, '联系我们', 'Contact')}</h4>
          <ul className="space-y-2">
            <li>
              <a href="https://qm.qq.com/q/1087471835" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-300 transition">
                {t(lang, 'QQ 群', 'QQ Group')}{' '}
                <span className="text-brand-400/80 font-mono text-xs">1087471835</span>
              </a>
            </li>
            <li>
              <a href="https://discord.gg/QABg4Z2Mzu" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-300 transition">
                Discord
              </a>
            </li>
            <li>
              <a href="https://x.com/dadoudou90" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-300 transition">
                X (Twitter)
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-300 mb-3">{t(lang, '技术驱动', 'Powered By')}</h4>
          <ul className="space-y-2">
            <li><a href="https://github.com/nicepkg/openclaw" className="text-gray-500 hover:text-gray-300 transition">OpenClaw</a></li>
            <li><a href="https://platform.deepseek.com/" className="text-gray-500 hover:text-gray-300 transition">DeepSeek</a></li>
            <li><a href="https://bailian.console.aliyun.com/" className="text-gray-500 hover:text-gray-300 transition">{t(lang, '百炼', 'Bailian')}</a></li>
          </ul>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/5 py-6 px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>🐾</span>
            <span>
              <strong className="text-gray-500">xyvaClaw</strong> — {t(lang, '从 Claw 到 xyvaClaw，不是替代，是进化。', 'From Claw to xyvaClaw, not a replacement, but an evolution.')}
            </span>
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-600">
            {t(lang, '由', 'By')}{' '}
            <a href="https://github.com/xyva-yuangui" target="_blank" rel="noopener noreferrer" className="text-brand-400/70 hover:text-brand-300 transition mx-1">
              Xyva-yuangui（圆规）
            </a>{' '}
            {t(lang, '用', 'made with')} <Heart size={14} className="text-red-500/60 mx-0.5" /> {t(lang, '打造', '')} · MIT · {new Date().getFullYear()}
          </div>
        </div>
      </div>
    </footer>
  );
}
