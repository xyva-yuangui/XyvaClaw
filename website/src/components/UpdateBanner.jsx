import React, { useState, useEffect } from 'react';
import { X, ArrowUpRight } from 'lucide-react';
import { useLang, t } from '../i18n';

const REPO = 'xyva-yuangui/XyvaClaw';
const STORAGE_KEY = 'xyvaclaw_dismissed_version';

export default function UpdateBanner() {
  const { lang } = useLang();
  const [release, setRelease] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    fetch(`https://api.github.com/repos/${REPO}/releases/latest`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data || !data.tag_name) return;
        if (stored === data.tag_name) return;
        setRelease({
          version: data.tag_name,
          name: data.name || data.tag_name,
          url: data.html_url,
          date: new Date(data.published_at).toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US'),
        });
      })
      .catch(() => {});

    if (!stored) {
      fetch(`https://api.github.com/repos/${REPO}/commits/main`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => {
          if (!data || !data.sha) return;
          const shortSha = data.sha.slice(0, 7);
          const version = `v0.0.0-${shortSha}`;
          if (stored === version) return;
          setRelease((prev) => prev || {
            version,
            name: data.commit?.message?.split('\n')[0] || 'Latest update',
            url: `https://github.com/${REPO}/commit/${data.sha}`,
            date: new Date(data.commit?.committer?.date).toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US'),
          });
        })
        .catch(() => {});
    }
  }, [lang]);

  const handleDismiss = () => {
    if (release) localStorage.setItem(STORAGE_KEY, release.version);
    setDismissed(true);
  };

  if (!release || dismissed) return null;

  return (
    <div className="fixed top-16 left-0 right-0 z-40 flex justify-center px-4 pointer-events-none">
      <div className="pointer-events-auto mt-2 flex items-center gap-3 px-4 py-2.5 rounded-xl bg-brand-600/15 border border-brand-500/30 backdrop-blur-xl shadow-lg shadow-brand-600/10 max-w-lg animate-slide-down">
        <span className="flex-shrink-0 w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        <div className="flex items-center gap-2 text-sm min-w-0">
          <span className="text-brand-300 font-mono font-semibold flex-shrink-0">{release.version}</span>
          <span className="text-gray-400 truncate hidden sm:inline">
            {t(lang, `更新于 ${release.date}`, `Updated ${release.date}`)}
          </span>
        </div>
        <a
          href={release.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200 transition flex-shrink-0 font-medium"
        >
          {t(lang, '查看', 'View')}
          <ArrowUpRight size={12} />
        </a>
        <button
          onClick={handleDismiss}
          className="text-gray-500 hover:text-gray-300 transition flex-shrink-0 ml-1"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
