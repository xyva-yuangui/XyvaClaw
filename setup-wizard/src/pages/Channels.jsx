import React from 'react';
import ApiKeyInput from '../components/ApiKeyInput';

const CHANNEL_LIST = [
  {
    id: 'feishu',
    name: '飞书 (Feishu/Lark)',
    icon: '💬',
    desc: '通过飞书机器人与 AI 助手对话',
    status: 'available',
    fields: [
      { key: 'appId', label: 'App ID', placeholder: 'cli_...' },
      { key: 'appSecret', label: 'App Secret', placeholder: '' },
    ],
    helpUrl: 'https://open.feishu.cn/',
    helpText: '如何创建飞书应用？',
    setupSteps: [
      '登录飞书开放平台 (open.feishu.cn) → 创建企业自建应用',
      '添加「机器人」能力 → 获取 App ID 和 App Secret',
      '事件与回调 → 订阅方式选择「使用长连接接收事件」(WebSocket)',
      '事件与回调 → 添加事件：接收消息 (im.message.receive_v1)',
      '权限管理 → 开通：获取与发送单聊/群组消息、读取群信息',
      '版本管理与发布 → 创建版本并发布上线',
      '将机器人拉入飞书群 → @机器人 即可对话',
    ],
  },
  {
    id: 'dingtalk',
    name: '钉钉 (DingTalk)',
    icon: '📌',
    desc: '通过钉钉机器人与 AI 助手对话',
    status: 'coming',
  },
  {
    id: 'telegram',
    name: 'Telegram',
    icon: '✈️',
    desc: '通过 Telegram Bot 对话',
    status: 'coming',
  },
  {
    id: 'webchat',
    name: 'Web Chat',
    icon: '🌐',
    desc: '通过浏览器直接与 AI 助手对话（默认启用）',
    status: 'available',
    alwaysOn: true,
  },
];

export default function Channels({ config, updateConfig }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">配置消息通道</h2>
        <p className="text-gray-500 mt-1">选择你想要的对话方式</p>
      </div>

      {CHANNEL_LIST.map((ch) => {
        const chConfig = config.channels[ch.id] || {};
        const enabled = ch.alwaysOn || chConfig.enabled;
        const isComing = ch.status === 'coming';

        return (
          <div
            key={ch.id}
            className={`border-2 rounded-xl p-5 transition ${
              isComing
                ? 'border-gray-100 bg-gray-50 opacity-60'
                : enabled
                ? 'border-brand-300 bg-brand-50/50'
                : 'border-gray-200'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <span className="text-2xl">{ch.icon}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{ch.name}</h3>
                    {isComing && (
                      <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full">
                        即将支持
                      </span>
                    )}
                    {ch.alwaysOn && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                        默认启用
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">{ch.desc}</p>
                </div>
              </div>

              {!ch.alwaysOn && !isComing && (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={chConfig.enabled || false}
                    onChange={(e) =>
                      updateConfig(`channels.${ch.id}.enabled`, e.target.checked)
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-brand-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
                </label>
              )}
            </div>

            {/* Feishu config fields */}
            {ch.id === 'feishu' && chConfig.enabled && (
              <div className="mt-4 space-y-4 pl-10">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    App ID
                  </label>
                  <input
                    type="text"
                    value={chConfig.appId || ''}
                    onChange={(e) =>
                      updateConfig('channels.feishu.appId', e.target.value)
                    }
                    placeholder="cli_..."
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-brand-400"
                  />
                </div>
                <ApiKeyInput
                  label="App Secret"
                  value={chConfig.appSecret || ''}
                  onChange={(val) =>
                    updateConfig('channels.feishu.appSecret', val)
                  }
                  placeholder="飞书应用密钥"
                  provider="feishu"
                  helpUrl={ch.helpUrl}
                  helpText={ch.helpText}
                  extraBody={{ appId: chConfig.appId }}
                />

                {/* Setup guide */}
                {ch.setupSteps && (
                  <details className="text-sm">
                    <summary className="text-brand-600 cursor-pointer hover:text-brand-700">
                      📖 飞书应用配置步骤
                    </summary>
                    <ol className="mt-2 space-y-1 text-gray-600 list-decimal list-inside">
                      {ch.setupSteps.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ol>
                  </details>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
