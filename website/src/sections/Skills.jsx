import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const GROUPS = [
  {
    label: 'Core',
    labelZh: '核心',
    color: 'bg-green-500',
    skills: [
      { name: 'secret-manager', desc: 'Secure API key management' },
      { name: 'claw-shell', desc: 'Terminal command execution' },
      { name: 'error-guard', desc: 'Automatic error handling' },
      { name: 'vision-reader', desc: 'Image/OCR recognition' },
      { name: 'browser-pilot', desc: 'Browser automation (Chrome)' },
      { name: 'git', desc: 'Version control operations' },
    ],
  },
  {
    label: 'Content Creation',
    labelZh: '内容创作',
    color: 'bg-brand-500',
    skills: [
      { name: 'content-creator', desc: 'Multi-platform content' },
      { name: 'auto-video-creator', desc: 'AI video generation' },
      { name: 'python-dataviz', desc: 'Data visualization' },
      { name: 'chart-image', desc: 'Chart generation' },
      { name: 'excel-xlsx', desc: 'Excel read/write' },
      { name: 'word-docx', desc: 'Word document generation' },
    ],
  },
  {
    label: 'Feishu Enhanced',
    labelZh: '飞书增强',
    color: 'bg-purple-500',
    skills: [
      { name: 'feishu-doc-extended', desc: 'Advanced doc ops (images, tables)' },
      { name: 'smart-messenger', desc: 'Enhanced message management' },
    ],
  },
  {
    label: 'Data & Quantitative',
    labelZh: '数据与量化',
    color: 'bg-amber-500',
    skills: [
      { name: 'quant-strategy-engine', desc: 'A-share stock screening' },
      { name: 'auto-researcher', desc: 'Automated research & analysis' },
      { name: 'rag-knowledge-base', desc: 'Local RAG knowledge base' },
      { name: 'knowledge-graph-memory', desc: 'Graph-based long-term memory' },
    ],
  },
  {
    label: 'Automation',
    labelZh: '自动化',
    color: 'bg-sky-500',
    skills: [
      { name: 'system-control', desc: 'Screenshots, system info' },
      { name: 'web-scraper', desc: 'Web content extraction' },
      { name: 'cron-scheduler', desc: 'Timed task execution' },
      { name: 'workflow', desc: 'Multi-step automation' },
      { name: 'batch', desc: 'Bulk task processing' },
      { name: 'screenshot-sender', desc: 'Capture and send screenshots' },
      { name: 'video-subtitles', desc: 'Video subtitle generation' },
      { name: 'qwen-image', desc: 'AI image generation' },
    ],
  },
  {
    label: 'Self-Evolution',
    labelZh: '自我进化',
    color: 'bg-rose-500',
    skills: [
      { name: 'self-improving-agent', desc: 'Learn from mistakes' },
      { name: 'proactive-agent', desc: 'Autonomous task discovery' },
      { name: 'effect-tracker', desc: 'Decision outcome tracking' },
      { name: 'code-review', desc: 'Automated code review' },
      { name: 'test-runner', desc: 'Automated testing' },
    ],
  },
  {
    label: 'Social Media',
    labelZh: '社交媒体',
    color: 'bg-pink-500',
    skills: [
      { name: 'xhs-creator', desc: 'Xiaohongshu content creation' },
      { name: 'xhs-publisher', desc: 'Xiaohongshu auto-publishing' },
      { name: 'reddit-readonly', desc: 'Reddit content scraping' },
      { name: 'miniflux-news', desc: 'RSS news aggregation' },
    ],
  },
];

export default function Skills() {
  const [expanded, setExpanded] = useState(new Set(['Core']));

  const toggle = (label) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const totalSkills = GROUPS.reduce((acc, g) => acc + g.skills.length, 0);

  return (
    <section id="skills" className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            <span className="gradient-text">{totalSkills} Skills.</span> Pre-installed.
          </h2>
          <p className="text-gray-400 text-lg">
            不需要额外安装，开箱即用
          </p>
        </div>

        <div className="space-y-3">
          {GROUPS.map((group) => {
            const isOpen = expanded.has(group.label);
            return (
              <div
                key={group.label}
                className="border border-white/5 rounded-xl overflow-hidden bg-white/[0.01] hover:bg-white/[0.02] transition"
              >
                <button
                  onClick={() => toggle(group.label)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${group.color}`} />
                    <span className="font-semibold text-white">{group.label}</span>
                    <span className="text-sm text-gray-500">{group.labelZh}</span>
                    <span className="text-xs text-gray-600 bg-white/5 px-2 py-0.5 rounded-full">
                      {group.skills.length}
                    </span>
                  </div>
                  <ChevronDown
                    size={18}
                    className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {group.skills.map((skill) => (
                      <div
                        key={skill.name}
                        className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-white/[0.02] border border-white/5"
                      >
                        <code className="text-xs text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded font-mono shrink-0 mt-0.5">
                          {skill.name}
                        </code>
                        <span className="text-sm text-gray-400">{skill.desc}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
