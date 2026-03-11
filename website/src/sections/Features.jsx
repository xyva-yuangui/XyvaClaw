import React from 'react';
import { Brain, RefreshCw, Zap, MessageSquare, Shield, TrendingUp } from 'lucide-react';

const FEATURES = [
  {
    icon: Brain,
    title: 'Deep Understanding',
    titleZh: '深度理解',
    desc: 'Lossless context engine with 4-tier memory system. Never loses context mid-conversation.',
    descZh: '无损上下文引擎 + 四层记忆系统，对话再长也不会"忘事"',
    color: 'brand',
    gradient: 'from-brand-500/20 to-brand-600/5',
  },
  {
    icon: TrendingUp,
    title: 'Advanced Reasoning',
    titleZh: '深度推理',
    desc: 'Auto-selects the optimal model per task complexity. DeepSeek Reasoner for hard problems, V3.2 for daily chat.',
    descZh: '根据任务复杂度自动选择最佳模型，推理模型处理复杂问题',
    color: 'purple',
    gradient: 'from-purple-500/20 to-purple-600/5',
  },
  {
    icon: RefreshCw,
    title: 'Self-Evolution',
    titleZh: '自我进化',
    desc: 'Error learning, effect tracking, proactive reflection. The longer you use it, the smarter it gets.',
    descZh: '错误学习 + 效果追踪 + 主动反思，越用越聪明',
    color: 'amber',
    gradient: 'from-amber-500/20 to-amber-600/5',
  },
  {
    icon: Zap,
    title: '38+ Built-in Skills',
    titleZh: '38+ 内置技能',
    desc: 'Browser automation, quant trading, content creation, document processing — all pre-installed.',
    descZh: '浏览器自动化、量化选股、内容创作、文档处理，开箱即用',
    color: 'green',
    gradient: 'from-green-500/20 to-green-600/5',
  },
  {
    icon: MessageSquare,
    title: 'Deep Feishu Integration',
    titleZh: '飞书深度集成',
    desc: '112 TypeScript files covering nearly every Feishu API. Docs, tables, calendar, approval, drive.',
    descZh: '112 个 TS 文件覆盖飞书几乎所有 API：文档、表格、日历、审批',
    color: 'sky',
    gradient: 'from-sky-500/20 to-sky-600/5',
  },
  {
    icon: Shield,
    title: '5-Level Fallback',
    titleZh: '五级模型容灾',
    desc: 'DeepSeek → Qwen3.5 → Kimi → Reasoner → Qwen3-Max. Zero downtime, always available.',
    descZh: '五级自动切换，任何模型故障都不影响服务',
    color: 'rose',
    gradient: 'from-rose-500/20 to-rose-600/5',
  },
];

const COLOR_MAP = {
  brand: 'text-brand-400 bg-brand-500/10 border-brand-500/20',
  purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  green: 'text-green-400 bg-green-500/10 border-green-500/20',
  sky: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
  rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
};

export default function Features() {
  return (
    <section id="features" className="py-24 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-5xl font-bold mb-4">
            Not just a chatbot.
            <br />
            <span className="gradient-text">A digital partner.</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            不只是聊天机器人，是能思考、行动、学习、进化的数字伙伴
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            const colors = COLOR_MAP[f.color];
            return (
              <div
                key={f.title}
                className={`group relative p-6 rounded-2xl bg-gradient-to-br ${f.gradient} border border-white/5 hover:border-white/10 transition-all duration-300 hover:-translate-y-1`}
              >
                <div className={`inline-flex p-3 rounded-xl border ${colors} mb-4`}>
                  <Icon size={24} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-1">{f.title}</h3>
                <p className="text-sm text-brand-300/70 mb-2">{f.titleZh}</p>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
                <p className="text-gray-500 text-xs mt-1">{f.descZh}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
