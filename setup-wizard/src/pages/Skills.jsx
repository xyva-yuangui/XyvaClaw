import React from 'react';

const SKILL_GROUPS = [
  {
    label: '核心技能（默认安装）',
    core: true,
    skills: [
      { id: 'secret-manager', name: '密钥管理', desc: '安全管理 API Key 和敏感信息' },
      { id: 'claw-shell', name: 'Shell 执行', desc: '在终端中执行命令' },
      { id: 'error-guard', name: '错误防护', desc: '自动捕获和处理错误' },
      { id: 'vision-reader', name: '图片/OCR 识别', desc: '识别图片中的文字和内容' },
      { id: 'browser-pilot', name: '浏览器自动化', desc: '自动操作浏览器完成任务' },
      { id: 'git', name: 'Git 管理', desc: 'Git 版本控制操作' },
    ],
  },
  {
    label: '内容创作',
    skills: [
      { id: 'content-creator', name: '内容创作', desc: '多平台内容生成和编辑' },
      { id: 'auto-video-creator', name: '自动视频', desc: 'AI 自动生成视频内容' },
      { id: 'python-dataviz', name: 'Python 可视化', desc: '数据图表生成' },
      { id: 'chart-image', name: '图表生成', desc: '快速生成各种图表' },
      { id: 'excel-xlsx', name: 'Excel 处理', desc: 'Excel/XLSX 文件读写' },
      { id: 'word-docx-1.0.0', name: 'Word 文档', desc: 'Word/DOCX 文件生成' },
    ],
  },
  {
    label: '飞书增强',
    condition: 'feishu',
    skills: [
      { id: 'feishu-doc-extended', name: '飞书文档增强', desc: '高级飞书文档操作（图片、表格等）' },
      { id: 'smart-messenger', name: '智能消息', desc: '增强的消息发送和管理' },
    ],
  },
  {
    label: '数据与量化',
    skills: [
      { id: 'quant-strategy-engine', name: '量化选股引擎', desc: 'A股量化策略筛选', requires: 'TUSHARE_TOKEN' },
      { id: 'auto-researcher', name: '自动研究', desc: '自动化信息研究和分析' },
      { id: 'rag-knowledge-base', name: '知识库 RAG', desc: '本地知识库检索增强' },
      { id: 'knowledge-graph-memory', name: '知识图谱记忆', desc: '图谱化的长期记忆' },
    ],
  },
  {
    label: '社交媒体',
    skills: [
      { id: 'xhs-creator', name: '小红书创作', desc: '小红书内容生成', requires: 'XHS_COOKIE' },
      { id: 'xhs-publisher', name: '小红书发布', desc: '自动发布到小红书', requires: 'XHS_COOKIE' },
      { id: 'reddit-readonly-1.0.0', name: 'Reddit 阅读', desc: 'Reddit 内容抓取和翻译' },
    ],
  },
  {
    label: '系统与自动化',
    skills: [
      { id: 'system-control', name: '系统控制', desc: '截屏、系统信息等' },
      { id: 'web-scraper', name: '网页抓取', desc: '自动抓取网页内容' },
      { id: 'cron-scheduler', name: '定时任务', desc: '定时执行任务' },
      { id: 'workflow', name: '工作流', desc: '多步骤自动化工作流' },
      { id: 'batch', name: '批量处理', desc: '批量执行任务' },
      { id: 'screenshot-sender', name: '截图发送', desc: '截屏并发送到聊天' },
      { id: 'video-subtitles', name: '视频字幕', desc: '视频字幕生成' },
      { id: 'qwen-image', name: '图片生成', desc: 'AI 图片生成 (万象)' },
    ],
  },
  {
    label: '自我进化',
    skills: [
      { id: 'self-improving-agent-1.0.11', name: '自我进化', desc: '从错误中学习，持续改进' },
      { id: 'proactive-agent-3.1.0', name: '主动行动', desc: '主动发现并执行任务' },
      { id: 'effect-tracker', name: '效果追踪', desc: '追踪决策和行动效果' },
      { id: 'test-runner', name: '测试运行', desc: '自动运行测试' },
      { id: 'code-review', name: '代码审查', desc: '自动代码审查' },
    ],
  },
];

export default function Skills({ config, updateConfig }) {
  const selected = new Set(config.skills.selected);
  const core = new Set(config.skills.core);

  const toggle = (id) => {
    const next = new Set(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    updateConfig('skills.selected', [...next]);
  };

  const selectAll = (groupSkills) => {
    const next = new Set(selected);
    groupSkills.forEach((s) => next.add(s.id));
    updateConfig('skills.selected', [...next]);
  };

  const totalSelected = core.size + selected.size;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">选择安装的技能</h2>
          <p className="text-gray-500 mt-1">
            已选 <span className="font-semibold text-brand-600">{totalSelected}</span> 个技能
          </p>
        </div>
      </div>

      {SKILL_GROUPS.map((group) => (
        <div key={group.label}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider">
              {group.label}
            </h3>
            {!group.core && (
              <button
                onClick={() => selectAll(group.skills)}
                className="text-xs text-brand-500 hover:text-brand-700"
              >
                全选
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {group.skills.map((skill) => {
              const isCore = core.has(skill.id);
              const isSelected = isCore || selected.has(skill.id);

              return (
                <label
                  key={skill.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition ${
                    isCore
                      ? 'border-green-200 bg-green-50 cursor-default'
                      : isSelected
                      ? 'border-brand-300 bg-brand-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isCore}
                    onChange={() => !isCore && toggle(skill.id)}
                    className="mt-0.5 text-brand-600 focus:ring-brand-400 rounded"
                  />
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium text-gray-900">
                        {skill.name}
                      </span>
                      {isCore && (
                        <span className="text-[10px] bg-green-200 text-green-800 px-1.5 py-0.5 rounded">
                          核心
                        </span>
                      )}
                      {skill.requires && (
                        <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                          需要 {skill.requires}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{skill.desc}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
