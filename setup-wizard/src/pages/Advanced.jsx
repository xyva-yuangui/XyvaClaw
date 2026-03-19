import React from 'react';

export default function Advanced({ config, updateConfig }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">高级设置</h2>
        <p className="text-gray-500 mt-1">大多数情况下使用默认值即可</p>
      </div>

      {/* Gateway Port */}
      <div className="border border-gray-200 rounded-xl p-5 space-y-3">
        <h3 className="font-semibold text-gray-900">Gateway 端口</h3>
        <p className="text-sm text-gray-500">
          AI 助手网关监听的端口号。如果默认端口被占用，可以修改。
        </p>
        <div className="flex items-center gap-3">
          <input
            type="number"
            value={config.gateway.port}
            onChange={(e) =>
              updateConfig('gateway.port', parseInt(e.target.value) || 18789)
            }
            min={1024}
            max={65535}
            className="w-32 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-brand-400"
          />
          <span className="text-sm text-gray-400">默认: 18789</span>
        </div>
      </div>

      {/* Auto Start */}
      <div className="border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">开机自启动</h3>
            <p className="text-sm text-gray-500 mt-1">
              系统启动时自动运行 AI 助手（推荐）
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.gateway.autoStart}
              onChange={(e) =>
                updateConfig('gateway.autoStart', e.target.checked)
              }
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-brand-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
          </label>
        </div>
      </div>

      {/* Context Engine */}
      <div className="border border-gray-200 rounded-xl p-5 space-y-3">
        <h3 className="font-semibold text-gray-900">上下文引擎</h3>
        <p className="text-sm text-gray-500">
          Lossless-Claw 无损上下文引擎，大幅提升长对话质量（推荐启用）
        </p>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
            已内置
          </span>
          <span className="text-xs text-gray-400">默认启用，无需额外配置</span>
        </div>
      </div>

      {/* Data Directory */}
      <div className="border border-gray-200 rounded-xl p-5 space-y-2">
        <h3 className="font-semibold text-gray-900">数据目录</h3>
        <p className="text-sm text-gray-500">
          所有配置、记忆、日志存储在此目录
        </p>
        <div className="bg-gray-50 rounded-lg px-3 py-2 text-sm font-mono text-gray-600">
          ~/.xyvaclaw
        </div>
        <p className="text-xs text-gray-400">
          通过环境变量 OPENCLAW_HOME 指定，安装时自动设置
        </p>
      </div>

      {/* Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
        <p className="font-medium mb-1">💡 提示</p>
        <ul className="space-y-1 text-blue-600">
          <li>
            - 如果你在服务器上部署，建议开启自启动以保证稳定运行
          </li>
          <li>
            - 端口需要确保防火墙允许访问（用于飞书 webhook 回调）
          </li>
          <li>
            - 所有设置后续都可以通过编辑 ~/.xyvaclaw/openclaw.json 修改
          </li>
        </ul>
      </div>
    </div>
  );
}
