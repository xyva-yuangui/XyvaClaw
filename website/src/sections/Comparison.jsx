import React from 'react';
import { Check, X, Minus } from 'lucide-react';
import { useLang, t } from '../i18n';

const ROWS = [
  { en: 'Setup', zh: '安装', openclaw: { en: 'Manual JSON editing', zh: '手动编辑 JSON' }, xyvaclaw: { en: 'One-click + Web wizard', zh: '一键安装 + Web 向导' }, winner: 'xyva' },
  { en: 'Models', zh: '模型', openclaw: { en: 'BYO (bring your own)', zh: '自行配置' }, xyvaclaw: { en: 'Pre-configured 10+ models', zh: '预配置 10+ 模型' }, winner: 'xyva' },
  { en: 'Fallback', zh: '容灾', openclaw: { en: 'Single model', zh: '单模型' }, xyvaclaw: { en: '5-level auto fallback', zh: '五级自动切换' }, winner: 'xyva' },
  { en: 'Context', zh: '上下文', openclaw: { en: 'Lossy compression', zh: '有损压缩' }, xyvaclaw: { en: 'Lossless-Claw engine', zh: '无损上下文引擎' }, winner: 'xyva' },
  { en: 'Memory', zh: '记忆', openclaw: { en: 'Basic MEMORY.md', zh: '基础 MEMORY.md' }, xyvaclaw: { en: '4-tier + knowledge graph', zh: '四层记忆 + 知识图谱' }, winner: 'xyva' },
  { en: 'Feishu', zh: '飞书', openclaw: { en: 'Basic messaging', zh: '基础消息收发' }, xyvaclaw: { en: '112 TS files, full API', zh: '112 个 TS 文件，全 API' }, winner: 'xyva' },
  { en: 'Skills', zh: '技能', openclaw: { en: 'Install one-by-one', zh: '逐个安装' }, xyvaclaw: { en: '38 pre-installed', zh: '38 个预装' }, winner: 'xyva' },
  { en: 'Self-Evolution', zh: '自我进化', openclaw: { en: '—', zh: '—' }, xyvaclaw: { en: 'Error learning + reflection', zh: '错误学习 + 主动反思' }, winner: 'xyva' },
  { en: 'Reasoning', zh: '推理', openclaw: { en: 'Manual model choice', zh: '手动选模型' }, xyvaclaw: { en: 'Auto-select per task', zh: '按任务自动选择' }, winner: 'xyva' },
  { en: 'Docs', zh: '文档', openclaw: { en: 'English only', zh: '仅英文' }, xyvaclaw: { en: 'CN + EN, with guides', zh: '中英文 + 教程' }, winner: 'xyva' },
  { en: 'Ops', zh: '运维', openclaw: { en: 'Manual', zh: '手动管理' }, xyvaclaw: { en: 'Health check + auto-start', zh: '健康检查 + 开机自启' }, winner: 'xyva' },
  { en: 'Runtime', zh: '运行时', openclaw: { en: 'OpenClaw core', zh: 'OpenClaw 核心' }, xyvaclaw: { en: 'Same OpenClaw core', zh: '相同 OpenClaw 核心' }, winner: 'tie' },
];

export default function Comparison() {
  const { lang } = useLang();
  return (
    <section id="comparison" className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            {t(lang, '相同引擎，', 'Same engine. ')}
            <span className="gradient-text">{t(lang, '全方位增强。', 'Everything else, better.')}</span>
          </h2>
          <p className="text-gray-400 text-lg">
            {t(lang, '基于 OpenClaw 运行时，系统级深度升级', 'Built on OpenClaw runtime, systematically enhanced')}
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-white/5">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left p-4 text-sm text-gray-400 font-medium">{t(lang, '维度', 'Feature')}</th>
                <th className="text-center p-4 text-sm text-gray-500 font-medium">OpenClaw</th>
                <th className="text-center p-4 text-sm font-medium">
                  <span className="gradient-text font-bold">xyvaClaw</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => {
                const ocText = t(lang, row.openclaw.zh, row.openclaw.en);
                const xcText = t(lang, row.xyvaclaw.zh, row.xyvaclaw.en);
                return (
                  <tr
                    key={row.en}
                    className={`border-b border-white/5 ${
                      i % 2 === 0 ? 'bg-white/[0.01]' : ''
                    } hover:bg-white/[0.03] transition`}
                  >
                    <td className="p-4 text-sm text-gray-300 font-medium">{t(lang, row.zh, row.en)}</td>
                    <td className="p-4 text-center text-sm text-gray-500">
                      {ocText === '—' ? (
                        <span className="inline-flex justify-center">
                          <X size={16} className="text-red-400/60" />
                        </span>
                      ) : (
                        ocText
                      )}
                    </td>
                    <td className="p-4 text-center text-sm">
                      <div className="flex items-center justify-center gap-2">
                        {row.winner === 'xyva' ? (
                          <span className="inline-flex items-center gap-1.5 text-brand-300 font-medium">
                            <Check size={14} className="text-green-400" />
                            {xcText}
                          </span>
                        ) : (
                          <span className="text-gray-400">{xcText}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
