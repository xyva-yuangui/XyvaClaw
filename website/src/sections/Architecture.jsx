import React from 'react';
import { FolderOpen, FileText, Puzzle, Brain, ScrollText } from 'lucide-react';
import { useLang, t } from '../i18n';

const TREE = [
  { name: '~/.xyvaclaw/', type: 'root', indent: 0 },
  { name: 'openclaw.json', en: 'Main configuration', zh: '主配置文件', indent: 1, icon: '⚙️' },
  { name: 'workspace/', type: 'dir', indent: 1 },
  { name: 'SOUL.md', en: 'AI personality definition', zh: 'AI 人格定义', indent: 2, icon: '🧬' },
  { name: 'AGENTS.md', en: 'Operating protocols', zh: '运行协议', indent: 2, icon: '📋' },
  { name: 'skills/', en: '38 skill modules', zh: '38 个技能模块', indent: 2, icon: '🛠' },
  { name: 'memory/', en: 'Persistent memory store', zh: '持久化记忆存储', indent: 2, icon: '🧠' },
  { name: 'extensions/', type: 'dir', indent: 1 },
  { name: 'feishu/', en: '112 TS files — deep integration', zh: '112 个 TS 文件 — 深度集成', indent: 2, icon: '💬' },
  { name: 'lossless-claw/', en: 'Context engine', zh: '无损上下文引擎', indent: 2, icon: '♾️' },
  { name: 'agents/', en: 'Multi-agent configurations', zh: '多智能体配置', indent: 1, icon: '👥' },
  { name: 'logs/', en: 'Runtime logs', zh: '运行日志', indent: 1, icon: '📝' },
];

const HIGHLIGHTS = [
  {
    icon: '🧬',
    en: { title: 'SOUL.md — Personality Core', desc: 'Defines who your AI assistant is: its values, communication style, and boundaries. Fully customizable.' },
    zh: { title: 'SOUL.md — 人格核心', desc: '定义 AI 助手的人格：价值观、沟通风格、行为边界，完全可自定义。' },
  },
  {
    icon: '🧠',
    en: { title: '4-Tier Memory System', desc: 'Session state → Daily journals → Long-term memory → Knowledge graph. Your assistant builds cognitive models over time.' },
    zh: { title: '四层记忆系统', desc: '会话状态 → 日记忆 → 长期记忆 → 知识图谱，助手随时间建立认知模型。' },
  },
  {
    icon: '🔄',
    en: { title: 'Evolution Engine', desc: '.learnings/ and .reflections/ directories store accumulated wisdom. The assistant improves autonomously.' },
    zh: { title: '进化引擎', desc: '.learnings/ 和 .reflections/ 存储积累的智慧，助手自主持续改进。' },
  },
  {
    icon: '🛡️',
    en: { title: 'Local-First Security', desc: 'All API keys, memory, and data stay on your machine. Nothing is sent to external servers.' },
    zh: { title: '本地优先安全', desc: '所有密钥、记忆、数据只存在本地，不上传任何外部服务器。' },
  },
];

export default function Architecture() {
  const { lang } = useLang();
  return (
    <section id="docs" className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            {t(lang, '清晰架构，', 'Clean architecture. ')}
            <span className="gradient-text">{t(lang, '完全透明。', 'Full transparency.')}</span>
          </h2>
          <p className="text-gray-400 text-lg">
            {t(lang, '每个文件都有明确职责，可审计可追溯', 'Every file has a clear responsibility, auditable and traceable')}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          <div className="rounded-2xl border border-white/10 bg-gray-900/50 p-6 overflow-hidden">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/5">
              <FolderOpen size={18} className="text-brand-400" />
              <span className="font-semibold text-gray-300">{t(lang, '项目结构', 'Project Structure')}</span>
            </div>
            <div className="font-mono text-sm space-y-1">
              {TREE.map((item, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2"
                  style={{ paddingLeft: `${item.indent * 20}px` }}
                >
                  {item.icon ? (
                    <span className="text-base w-5 text-center">{item.icon}</span>
                  ) : item.type === 'root' ? (
                    <FolderOpen size={14} className="text-brand-400" />
                  ) : item.type === 'dir' ? (
                    <FolderOpen size={14} className="text-yellow-500/60" />
                  ) : (
                    <FileText size={14} className="text-gray-600" />
                  )}
                  <span
                    className={
                      item.type === 'root'
                        ? 'text-brand-300 font-bold'
                        : item.type === 'dir'
                        ? 'text-yellow-400/80'
                        : 'text-gray-400'
                    }
                  >
                    {item.name}
                  </span>
                  {item.en && (
                    <span className="text-gray-600 text-xs ml-1">— {t(lang, item.zh, item.en)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-5">
            {HIGHLIGHTS.map((item) => {
              const data = lang === 'zh' ? item.zh : item.en;
              return (
                <div
                  key={item.en.title}
                  className="p-5 rounded-xl border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{item.icon}</span>
                    <h3 className="font-semibold text-white">{data.title}</h3>
                  </div>
                  <p className="text-sm text-gray-400 leading-relaxed">{data.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
