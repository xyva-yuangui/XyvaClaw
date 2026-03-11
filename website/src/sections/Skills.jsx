import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useLang, t } from '../i18n';

const GROUPS = [
  {
    en: 'Core', zh: '核心', color: 'bg-green-500',
    skills: [
      { name: 'secret-manager', en: 'Secure API key management', zh: '密钥安全管理' },
      { name: 'claw-shell', en: 'Terminal command execution', zh: '终端命令执行' },
      { name: 'error-guard', en: 'Automatic error handling', zh: '错误自动防护' },
      { name: 'vision-reader', en: 'Image/OCR recognition', zh: '图片/OCR 识别' },
      { name: 'browser-pilot', en: 'Browser automation (Chrome)', zh: '浏览器自动化 (Chrome)' },
      { name: 'git', en: 'Version control operations', zh: '版本控制操作' },
    ],
  },
  {
    en: 'Content Creation', zh: '内容创作', color: 'bg-brand-500',
    skills: [
      { name: 'content-creator', en: 'Multi-platform content', zh: '多平台内容创作' },
      { name: 'auto-video-creator', en: 'AI video generation', zh: 'AI 视频生成' },
      { name: 'python-dataviz', en: 'Data visualization', zh: '数据可视化' },
      { name: 'chart-image', en: 'Chart generation', zh: '图表生成' },
      { name: 'excel-xlsx', en: 'Excel read/write', zh: 'Excel 读写' },
      { name: 'word-docx', en: 'Word document generation', zh: 'Word 文档生成' },
    ],
  },
  {
    en: 'Feishu Enhanced', zh: '飞书增强', color: 'bg-purple-500',
    skills: [
      { name: 'feishu-doc-extended', en: 'Advanced doc ops (images, tables)', zh: '高级文档操作（图片、表格）' },
      { name: 'smart-messenger', en: 'Enhanced message management', zh: '增强消息管理' },
    ],
  },
  {
    en: 'Data & Quantitative', zh: '数据与量化', color: 'bg-amber-500',
    skills: [
      { name: 'quant-strategy-engine', en: 'A-share stock screening', zh: 'A 股量化选股' },
      { name: 'auto-researcher', en: 'Automated research & analysis', zh: '自动化研究分析' },
      { name: 'rag-knowledge-base', en: 'Local RAG knowledge base', zh: '本地 RAG 知识库' },
      { name: 'knowledge-graph-memory', en: 'Graph-based long-term memory', zh: '知识图谱长期记忆' },
    ],
  },
  {
    en: 'Automation', zh: '自动化', color: 'bg-sky-500',
    skills: [
      { name: 'system-control', en: 'Screenshots, system info', zh: '截图、系统信息' },
      { name: 'web-scraper', en: 'Web content extraction', zh: '网页内容抓取' },
      { name: 'cron-scheduler', en: 'Timed task execution', zh: '定时任务执行' },
      { name: 'workflow', en: 'Multi-step automation', zh: '多步骤自动化' },
      { name: 'batch', en: 'Bulk task processing', zh: '批量任务处理' },
      { name: 'screenshot-sender', en: 'Capture and send screenshots', zh: '截图发送' },
      { name: 'video-subtitles', en: 'Video subtitle generation', zh: '视频字幕生成' },
      { name: 'qwen-image', en: 'AI image generation', zh: 'AI 图片生成' },
    ],
  },
  {
    en: 'Self-Evolution', zh: '自我进化', color: 'bg-rose-500',
    skills: [
      { name: 'self-improving-agent', en: 'Learn from mistakes', zh: '从错误中学习' },
      { name: 'proactive-agent', en: 'Autonomous task discovery', zh: '自主发现任务' },
      { name: 'effect-tracker', en: 'Decision outcome tracking', zh: '决策效果追踪' },
      { name: 'code-review', en: 'Automated code review', zh: '自动代码审查' },
      { name: 'test-runner', en: 'Automated testing', zh: '自动化测试' },
    ],
  },
  {
    en: 'Social Media', zh: '社交媒体', color: 'bg-pink-500',
    skills: [
      { name: 'xhs-creator', en: 'Xiaohongshu content creation', zh: '小红书内容创作' },
      { name: 'xhs-publisher', en: 'Xiaohongshu auto-publishing', zh: '小红书自动发布' },
      { name: 'reddit-readonly', en: 'Reddit content scraping', zh: 'Reddit 内容抓取' },
      { name: 'miniflux-news', en: 'RSS news aggregation', zh: 'RSS 新闻聚合' },
    ],
  },
];

export default function Skills() {
  const { lang } = useLang();
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
            <span className="gradient-text">{totalSkills} {t(lang, '个技能', 'Skills')}.</span>{' '}
            {t(lang, '开箱即用。', 'Pre-installed.')}
          </h2>
          <p className="text-gray-400 text-lg">
            {t(lang, '不需要额外安装，全部预装完毕', 'No extra installation needed, everything is ready')}
          </p>
        </div>

        <div className="space-y-3">
          {GROUPS.map((group) => {
            const isOpen = expanded.has(group.en);
            return (
              <div
                key={group.en}
                className="border border-white/5 rounded-xl overflow-hidden bg-white/[0.01] hover:bg-white/[0.02] transition"
              >
                <button
                  onClick={() => toggle(group.en)}
                  className="w-full flex items-center justify-between p-5 text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${group.color}`} />
                    <span className="font-semibold text-white">{t(lang, group.zh, group.en)}</span>
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
                        <span className="text-sm text-gray-400">{t(lang, skill.zh, skill.en)}</span>
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
