import React, { useState } from 'react';
import ApiKeyInput from '../components/ApiKeyInput';

const PROVIDERS = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    desc: '性价比高，推荐首选。支持 V3.2 和 Reasoner 推理模型',
    placeholder: 'sk-...',
    helpUrl: 'https://platform.deepseek.com/api_keys',
    models: ['deepseek-chat (V3.2)', 'deepseek-reasoner (R1)'],
  },
  {
    id: 'bailian',
    name: '百炼 (通义千问)',
    desc: '阿里云百炼平台，支持 Qwen、Kimi、GLM、MiniMax 等多种模型',
    placeholder: 'sk-sp-...',
    helpUrl: 'https://bailian.console.aliyun.com/',
    models: ['qwen3.5-plus', 'qwen3-max', 'kimi-k2.5', 'glm-5', 'MiniMax-M2.5'],
  },
];

export default function ModelKeys({ config, updateConfig }) {
  const [showCustom, setShowCustom] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [customKey, setCustomKey] = useState('');
  const [customModels, setCustomModels] = useState('');
  const [detecting, setDetecting] = useState(false);
  const [detectError, setDetectError] = useState('');
  const [detectedModels, setDetectedModels] = useState([]);

  const hasAnyProvider =
    config.providers.deepseek.enabled ||
    config.providers.bailian.enabled ||
    config.providers.custom.length > 0;

  const detectModels = async () => {
    if (!customUrl || !customKey) return;
    setDetecting(true);
    setDetectError('');
    setDetectedModels([]);
    try {
      const res = await fetch('/api/detect-models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseUrl: customUrl, apiKey: customKey }),
      });
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        setDetectedModels(data.models);
        setCustomModels(data.models.map((m) => m.id).join(', '));
      } else {
        setDetectError(data.error || '未检测到模型，请手动输入模型 ID');
      }
    } catch {
      setDetectError('检测失败，请手动输入模型 ID');
    } finally {
      setDetecting(false);
    }
  };

  const parseModelsFromInput = (input) => {
    return input
      .split(/[,，\n]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((id) => {
        const detected = detectedModels.find((m) => m.id === id);
        return detected || { id, name: id, reasoning: false, input: ['text'], contextWindow: 128000, maxTokens: 4096 };
      });
  };

  const addCustomProvider = () => {
    if (!customName || !customUrl || !customKey) return;
    const models = parseModelsFromInput(customModels);
    const customs = [...config.providers.custom, { name: customName, baseUrl: customUrl, apiKey: customKey, models }];
    updateConfig('providers.custom', customs);
    setCustomName('');
    setCustomUrl('');
    setCustomKey('');
    setCustomModels('');
    setDetectedModels([]);
    setDetectError('');
    setShowCustom(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">配置 AI 模型</h2>
        <p className="text-gray-500 mt-1">至少需要配置一个模型 Provider</p>
      </div>

      {PROVIDERS.map((prov) => {
        const provConfig = config.providers[prov.id];
        return (
          <div
            key={prov.id}
            className={`border-2 rounded-xl p-5 transition ${
              provConfig.enabled
                ? 'border-brand-300 bg-brand-50/50'
                : 'border-gray-200'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">{prov.name}</h3>
                  {provConfig.verified && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                      已验证
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-0.5">{prov.desc}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={provConfig.enabled}
                  onChange={(e) =>
                    updateConfig(`providers.${prov.id}.enabled`, e.target.checked)
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-brand-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
              </label>
            </div>

            {provConfig.enabled && (
              <div className="space-y-3">
                <ApiKeyInput
                  label="API Key"
                  value={provConfig.apiKey}
                  onChange={(val) => updateConfig(`providers.${prov.id}.apiKey`, val)}
                  placeholder={prov.placeholder}
                  provider={prov.id}
                  verified={provConfig.verified}
                  helpUrl={prov.helpUrl}
                />
                <div className="flex flex-wrap gap-1.5">
                  {prov.models.map((m) => (
                    <span
                      key={m}
                      className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded"
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Custom providers */}
      {config.providers.custom.map((cp, i) => (
        <div key={i} className="border-2 border-green-200 bg-green-50/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="font-medium">{cp.name}</span>
              <span className="text-sm text-gray-400 ml-2">{cp.baseUrl}</span>
            </div>
            <button
              onClick={() => {
                const customs = config.providers.custom.filter((_, j) => j !== i);
                updateConfig('providers.custom', customs);
              }}
              className="text-red-400 hover:text-red-600 text-sm"
            >
              删除
            </button>
          </div>
          {cp.models && cp.models.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {cp.models.map((m) => (
                <span
                  key={typeof m === 'string' ? m : m.id}
                  className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded"
                >
                  {typeof m === 'string' ? m : m.id}
                </span>
              ))}
            </div>
          )}
          {(!cp.models || cp.models.length === 0) && (
            <p className="text-xs text-amber-600">⚠️ 未配置模型列表，Gateway 将无法使用此 Provider</p>
          )}
        </div>
      ))}

      {!showCustom ? (
        <button
          onClick={() => setShowCustom(true)}
          className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-brand-400 hover:text-brand-600 transition text-sm"
        >
          + 添加自定义 OpenAI 兼容 Provider
        </button>
      ) : (
        <div className="border-2 border-brand-200 rounded-xl p-5 bg-brand-50/30 space-y-3">
          <h3 className="font-medium text-gray-900">添加自定义 Provider</h3>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="名称 (如 openrouter)"
              className="px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
            <input
              type="text"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="Base URL (如 https://...)"
              className="px-3 py-2 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <div className="flex gap-2">
            <input
              type="password"
              value={customKey}
              onChange={(e) => setCustomKey(e.target.value)}
              placeholder="API Key"
              className="flex-1 px-3 py-2 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-brand-400"
            />
            <button
              onClick={detectModels}
              disabled={!customUrl || !customKey || detecting}
              className="px-4 py-2 text-sm border border-brand-300 text-brand-600 rounded-lg hover:bg-brand-50 disabled:opacity-40 disabled:cursor-not-allowed transition whitespace-nowrap"
            >
              {detecting ? '检测中...' : '🔍 检测模型'}
            </button>
          </div>
          {detectError && (
            <p className="text-xs text-amber-600">{detectError}</p>
          )}
          {detectedModels.length > 0 && (
            <div>
              <p className="text-xs text-green-600 mb-1">✅ 检测到 {detectedModels.length} 个模型（可编辑）</p>
            </div>
          )}
          <div>
            <label className="text-xs text-gray-500 mb-1 block">模型 ID（逗号分隔，或点击「检测模型」自动获取）</label>
            <textarea
              value={customModels}
              onChange={(e) => setCustomModels(e.target.value)}
              placeholder="如: gpt-4o, gpt-4o-mini, claude-3-5-sonnet"
              rows={2}
              className="w-full px-3 py-2 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-brand-400 resize-none"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowCustom(false)}
              className="px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg"
            >
              取消
            </button>
            <button
              onClick={addCustomProvider}
              disabled={!customName || !customUrl || !customKey || !customModels.trim()}
              className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-40"
            >
              添加
            </button>
          </div>
        </div>
      )}

      {!hasAnyProvider && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
          💡 至少需要启用一个模型 Provider 才能继续
        </div>
      )}
    </div>
  );
}
