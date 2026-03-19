import React, { useState } from 'react';
import Welcome from './pages/Welcome';
import ModelKeys from './pages/ModelKeys';
import Channels from './pages/Channels';
import Skills from './pages/Skills';
import Advanced from './pages/Advanced';
import Confirm from './pages/Confirm';
import StepIndicator from './components/StepIndicator';

const STEPS = [
  { id: 'welcome', label: '欢迎', icon: '👋' },
  { id: 'models', label: 'AI 模型', icon: '🧠' },
  { id: 'channels', label: '消息通道', icon: '📱' },
  { id: 'skills', label: '技能选装', icon: '🛠' },
  { id: 'advanced', label: '高级设置', icon: '⚙️' },
  { id: 'confirm', label: '确认启动', icon: '🚀' },
];

const DEFAULT_CONFIG = {
  assistantName: '',
  assistantStyle: 'balanced',
  providers: {
    deepseek: { enabled: false, apiKey: '', verified: false },
    bailian: { enabled: false, apiKey: '', verified: false },
    custom: [],
  },
  channels: {
    feishu: { enabled: false, appId: '', appSecret: '' },
    dingtalk: { enabled: false, appKey: '', appSecret: '' },
    webchat: { enabled: true },
  },
  skills: {
    core: ['secret-manager', 'claw-shell', 'error-guard', 'vision-reader', 'browser-pilot'],
    selected: [],
  },
  gateway: {
    port: 18789,
    autoStart: true,
  },
};

export default function App() {
  const [step, setStep] = useState(0);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const updateConfig = (path, value) => {
    setConfig((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      const keys = path.split('.');
      let obj = next;
      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/save-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      if (data.ok) {
        setDone(true);
      } else {
        alert('保存失败: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('保存失败: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const canGoNext = () => {
    if (step === 0) return config.assistantName.trim().length > 0;
    if (step === 1) {
      return (
        config.providers.deepseek.enabled ||
        config.providers.bailian.enabled ||
        config.providers.custom.length > 0
      );
    }
    return true;
  };

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-brand-100">
        <div className="bg-white rounded-2xl shadow-xl p-12 max-w-lg text-center">
          <div className="text-6xl mb-6">🎉</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">配置完成！</h1>
          <p className="text-gray-600 mb-6">
            你的 AI 助手 <strong>{config.assistantName}</strong> 已准备就绪。
          </p>
          <div className="bg-gray-50 rounded-lg p-4 text-left text-sm font-mono mb-6">
            <p className="text-gray-500 mb-1"># 启动你的 AI 助手</p>
            <p className="text-brand-600 font-semibold">xyvaclaw gateway</p>
          </div>
          <p className="text-gray-400 text-sm">你可以关闭此页面了。安装脚本会继续完成剩余步骤。</p>
        </div>
      </div>
    );
  }

  const pages = [
    <Welcome config={config} updateConfig={updateConfig} />,
    <ModelKeys config={config} updateConfig={updateConfig} />,
    <Channels config={config} updateConfig={updateConfig} />,
    <Skills config={config} updateConfig={updateConfig} />,
    <Advanced config={config} updateConfig={updateConfig} />,
    <Confirm config={config} onSave={handleSave} saving={saving} />,
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-brand-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            <span className="text-brand-600">xyva</span>Claw
          </h1>
          <p className="text-gray-500 mt-1">AI 助手配置向导</p>
        </div>

        {/* Step indicator */}
        <StepIndicator steps={STEPS} current={step} />

        {/* Page content */}
        <div className="mt-8 bg-white rounded-2xl shadow-lg p-8 min-h-[400px]">
          {pages[step]}
        </div>

        {/* Navigation */}
        <div className="mt-6 flex justify-between">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="px-6 py-2.5 rounded-lg text-gray-600 hover:bg-white hover:shadow disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            ← 上一步
          </button>

          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
              disabled={!canGoNext()}
              className="px-6 py-2.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium"
            >
              下一步 →
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
