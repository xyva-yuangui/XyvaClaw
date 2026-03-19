import React from 'react';

const STYLES = [
  { id: 'professional', label: '专业严谨', desc: '适合工作场景，回答精准简洁' },
  { id: 'balanced', label: '均衡友好', desc: '既专业又亲切，推荐大多数用户' },
  { id: 'casual', label: '轻松随和', desc: '像朋友一样聊天，有趣有温度' },
];

export default function Welcome({ config, updateConfig }) {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <div className="text-5xl mb-4">🐾</div>
        <h2 className="text-2xl font-bold text-gray-900">欢迎使用 xyvaClaw</h2>
        <p className="text-gray-500 mt-2">让我们花 2 分钟完成初始配置</p>
      </div>

      <div className="max-w-md mx-auto space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            给你的 AI 助手起个名字
          </label>
          <input
            type="text"
            value={config.assistantName}
            onChange={(e) => updateConfig('assistantName', e.target.value)}
            placeholder="例如：小助手、Jarvis、阿贾..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-400 focus:border-brand-400 outline-none text-lg"
            autoFocus
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            助手风格
          </label>
          <div className="space-y-2">
            {STYLES.map((style) => (
              <label
                key={style.id}
                className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition ${
                  config.assistantStyle === style.id
                    ? 'border-brand-400 bg-brand-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="style"
                  value={style.id}
                  checked={config.assistantStyle === style.id}
                  onChange={(e) => updateConfig('assistantStyle', e.target.value)}
                  className="text-brand-600 focus:ring-brand-400"
                />
                <div>
                  <div className="font-medium text-gray-900">{style.label}</div>
                  <div className="text-sm text-gray-500">{style.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
