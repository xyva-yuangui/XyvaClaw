import React from 'react';
import { FolderOpen, FileText, Puzzle, Brain, ScrollText } from 'lucide-react';

const TREE = [
  { name: '~/.xyvaclaw/', type: 'root', indent: 0 },
  { name: 'openclaw.json', desc: 'Main configuration', indent: 1, icon: '⚙️' },
  { name: 'workspace/', type: 'dir', indent: 1 },
  { name: 'SOUL.md', desc: 'AI personality definition', indent: 2, icon: '🧬' },
  { name: 'AGENTS.md', desc: 'Operating protocols', indent: 2, icon: '📋' },
  { name: 'skills/', desc: '38 skill modules', indent: 2, icon: '🛠' },
  { name: 'memory/', desc: 'Persistent memory store', indent: 2, icon: '🧠' },
  { name: 'extensions/', type: 'dir', indent: 1 },
  { name: 'feishu/', desc: '112 TS files — deep integration', indent: 2, icon: '💬' },
  { name: 'lossless-claw/', desc: 'Context engine', indent: 2, icon: '♾️' },
  { name: 'agents/', desc: 'Multi-agent configurations', indent: 1, icon: '👥' },
  { name: 'logs/', desc: 'Runtime logs', indent: 1, icon: '📝' },
];

export default function Architecture() {
  return (
    <section id="docs" className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            Clean architecture.{' '}
            <span className="gradient-text">Full transparency.</span>
          </h2>
          <p className="text-gray-400 text-lg">
            清晰的目录结构，每个文件都有明确职责
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          {/* File tree */}
          <div className="rounded-2xl border border-white/10 bg-gray-900/50 p-6 overflow-hidden">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/5">
              <FolderOpen size={18} className="text-brand-400" />
              <span className="font-semibold text-gray-300">Project Structure</span>
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
                  {item.desc && (
                    <span className="text-gray-600 text-xs ml-1">— {item.desc}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Architecture highlights */}
          <div className="space-y-5">
            {[
              {
                icon: '🧬',
                title: 'SOUL.md — Personality Core',
                desc: 'Defines who your AI assistant is: its values, communication style, and boundaries. Fully customizable.',
                descZh: '定义 AI 助手的人格：价值观、沟通风格、行为边界',
              },
              {
                icon: '🧠',
                title: '4-Tier Memory System',
                desc: 'Session state → Daily journals → Long-term memory → Knowledge graph. Your assistant builds cognitive models over time.',
                descZh: '会话状态 → 日记忆 → 长期记忆 → 知识图谱',
              },
              {
                icon: '🔄',
                title: 'Evolution Engine',
                desc: '.learnings/ and .reflections/ directories store accumulated wisdom. The assistant improves autonomously.',
                descZh: '学习日志和反思记录，助手自主持续改进',
              },
              {
                icon: '🛡️',
                title: 'Local-First Security',
                desc: 'All API keys, memory, and data stay on your machine. Nothing is sent to external servers.',
                descZh: '所有密钥、记忆、数据只存在本地，不上传任何服务器',
              },
            ].map((item) => (
              <div
                key={item.title}
                className="p-5 rounded-xl border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{item.icon}</span>
                  <h3 className="font-semibold text-white">{item.title}</h3>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                <p className="text-xs text-gray-600 mt-1">{item.descZh}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
