import React from 'react';
import { Check, X, Minus } from 'lucide-react';

const ROWS = [
  { feature: 'Setup / 安装', openclaw: 'Manual JSON editing', xyvaclaw: 'One-click + Web wizard', winner: 'xyva' },
  { feature: 'Models / 模型', openclaw: 'BYO (bring your own)', xyvaclaw: 'Pre-configured 10+ models', winner: 'xyva' },
  { feature: 'Fallback / 容灾', openclaw: 'Single model', xyvaclaw: '5-level auto fallback', winner: 'xyva' },
  { feature: 'Context / 上下文', openclaw: 'Lossy compression', xyvaclaw: 'Lossless-Claw engine', winner: 'xyva' },
  { feature: 'Memory / 记忆', openclaw: 'Basic MEMORY.md', xyvaclaw: '4-tier + knowledge graph', winner: 'xyva' },
  { feature: 'Feishu / 飞书', openclaw: 'Basic messaging', xyvaclaw: '112 TS files, full API', winner: 'xyva' },
  { feature: 'Skills / 技能', openclaw: 'Install one-by-one', xyvaclaw: '38 pre-installed', winner: 'xyva' },
  { feature: 'Self-Evolution / 进化', openclaw: '—', xyvaclaw: 'Error learning + reflection', winner: 'xyva' },
  { feature: 'Reasoning / 推理', openclaw: 'Manual model choice', xyvaclaw: 'Auto-select per task', winner: 'xyva' },
  { feature: 'Docs / 文档', openclaw: 'English only', xyvaclaw: 'CN + EN, with guides', winner: 'xyva' },
  { feature: 'Ops / 运维', openclaw: 'Manual', xyvaclaw: 'Health check + auto-start', winner: 'xyva' },
  { feature: 'Runtime / 运行时', openclaw: 'OpenClaw core', xyvaclaw: 'Same OpenClaw core', winner: 'tie' },
];

export default function Comparison() {
  return (
    <section id="comparison" className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            Same engine.{' '}
            <span className="gradient-text">Everything else, better.</span>
          </h2>
          <p className="text-gray-400 text-lg">
            相同引擎，全方位增强
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-white/5">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left p-4 text-sm text-gray-400 font-medium">Feature</th>
                <th className="text-center p-4 text-sm text-gray-500 font-medium">OpenClaw</th>
                <th className="text-center p-4 text-sm font-medium">
                  <span className="gradient-text font-bold">xyvaClaw</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`border-b border-white/5 ${
                    i % 2 === 0 ? 'bg-white/[0.01]' : ''
                  } hover:bg-white/[0.03] transition`}
                >
                  <td className="p-4 text-sm text-gray-300 font-medium">{row.feature}</td>
                  <td className="p-4 text-center text-sm text-gray-500">
                    {row.openclaw === '—' ? (
                      <span className="inline-flex justify-center">
                        <X size={16} className="text-red-400/60" />
                      </span>
                    ) : (
                      row.openclaw
                    )}
                  </td>
                  <td className="p-4 text-center text-sm">
                    <div className="flex items-center justify-center gap-2">
                      {row.winner === 'xyva' ? (
                        <span className="inline-flex items-center gap-1.5 text-brand-300 font-medium">
                          <Check size={14} className="text-green-400" />
                          {row.xyvaclaw}
                        </span>
                      ) : (
                        <span className="text-gray-400">{row.xyvaclaw}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
