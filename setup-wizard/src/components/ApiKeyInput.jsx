import React, { useState } from 'react';

export default function ApiKeyInput({
  label,
  value,
  onChange,
  placeholder,
  provider,
  verified,
  helpUrl,
  helpText,
}) {
  const [show, setShow] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(verified ? 'ok' : null);

  const handleVerify = async () => {
    if (!value.trim()) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await fetch('/api/validate-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, apiKey: value }),
      });
      const data = await res.json();
      setVerifyResult(data.valid ? 'ok' : 'fail');
    } catch {
      setVerifyResult('fail');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {helpUrl && (
          <a
            href={helpUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-500 hover:text-brand-700"
          >
            {helpText || '如何获取？'}
          </a>
        )}
      </div>
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type={show ? 'text' : 'password'}
            value={value}
            onChange={(e) => {
              onChange(e.target.value);
              setVerifyResult(null);
            }}
            placeholder={placeholder || 'sk-...'}
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-400 focus:border-brand-400 outline-none text-sm font-mono pr-10"
          />
          <button
            type="button"
            onClick={() => setShow(!show)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-sm"
          >
            {show ? '🙈' : '👁'}
          </button>
        </div>
        <button
          onClick={handleVerify}
          disabled={!value.trim() || verifying}
          className="px-4 py-2.5 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition whitespace-nowrap"
        >
          {verifying ? '验证中...' : '验证'}
        </button>
      </div>
      {verifyResult === 'ok' && (
        <p className="text-sm text-green-600 flex items-center gap-1">
          <span>✅</span> 验证通过
        </p>
      )}
      {verifyResult === 'fail' && (
        <p className="text-sm text-red-500 flex items-center gap-1">
          <span>❌</span> 验证失败，请检查 Key 是否正确
        </p>
      )}
    </div>
  );
}
