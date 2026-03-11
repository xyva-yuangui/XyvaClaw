import React from 'react';

export default function Confirm({ config, onSave, saving }) {
  const providers = [];
  if (config.providers.deepseek.enabled) providers.push('DeepSeek');
  if (config.providers.bailian.enabled) providers.push('百炼');
  config.providers.custom.forEach((c) => providers.push(c.name));

  const channels = [];
  if (config.channels.feishu.enabled) channels.push('飞书');
  if (config.channels.dingtalk?.enabled) channels.push('钉钉');
  channels.push('Web Chat');

  const allSkills = [...config.skills.core, ...config.skills.selected];

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="text-4xl mb-3">🚀</div>
        <h2 className="text-xl font-bold text-gray-900">确认配置</h2>
        <p className="text-gray-500 mt-1">检查以下配置是否正确，然后一键启动</p>
      </div>

      <div className="space-y-4">
        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <SummaryCard
            icon="🐾"
            title="AI 助手"
            items={[
              `名称: ${config.assistantName}`,
              `风格: ${
                { professional: '专业严谨', balanced: '均衡友好', casual: '轻松随和' }[
                  config.assistantStyle
                ]
              }`,
            ]}
          />
          <SummaryCard
            icon="🧠"
            title="AI 模型"
            items={
              providers.length > 0
                ? providers.map((p) => p)
                : ['⚠️ 未配置（需要至少一个）']
            }
          />
          <SummaryCard
            icon="📱"
            title="消息通道"
            items={channels}
          />
          <SummaryCard
            icon="⚙️"
            title="系统设置"
            items={[
              `Gateway 端口: ${config.gateway.port}`,
              `开机自启: ${config.gateway.autoStart ? '是' : '否'}`,
            ]}
          />
        </div>

        <div className="border border-gray-200 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              🛠 已选技能 ({allSkills.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {allSkills.map((s) => (
              <span
                key={s}
                className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Save button */}
      <div className="text-center pt-4">
        <button
          onClick={onSave}
          disabled={saving || providers.length === 0}
          className="px-8 py-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition font-semibold text-lg shadow-lg shadow-brand-200"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <svg
                className="animate-spin h-5 w-5"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              保存中...
            </span>
          ) : (
            '✨ 保存配置并完成'
          )}
        </button>

        {providers.length === 0 && (
          <p className="text-sm text-red-500 mt-2">
            请至少配置一个 AI 模型 Provider
          </p>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ icon, title, items }) {
  return (
    <div className="border border-gray-200 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <span>{icon}</span>
        <span className="font-semibold text-gray-900 text-sm">{title}</span>
      </div>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
