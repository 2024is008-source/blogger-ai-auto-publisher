import React, { useMemo, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import type { BlogAccount, PublishingHistoryRecord } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface PublishingHistoryPageProps {
  history: PublishingHistoryRecord[];
  blogs: BlogAccount[];
}

function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const PublishingHistoryPage: React.FC<PublishingHistoryPageProps> = ({ history, blogs }) => {
  const [blogFilter, setBlogFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [modeFilter, setModeFilter] = useState('ALL');
  const [keyword, setKeyword] = useState('');
  const [datePrefix, setDatePrefix] = useState('');

  const filtered = useMemo(() => {
    return history.filter((rec) => {
      if (blogFilter !== 'ALL' && rec.blog_id !== blogFilter) return false;
      if (statusFilter !== 'ALL' && rec.status !== statusFilter) return false;
      if (modeFilter !== 'ALL' && rec.publishing_mode !== modeFilter) return false;
      if (datePrefix && !rec.timestamp_utc.startsWith(datePrefix)) return false;
      if (keyword.trim()) {
        const q = keyword.toLowerCase();
        const hay = `${rec.article_title} ${rec.main_keyword} ${rec.blogger_post_id}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [history, blogFilter, statusFilter, modeFilter, keyword, datePrefix]);

  const exportCsv = () => {
    const headers = [
      'record_id',
      'article_id',
      'article_title',
      'blog_id',
      'blog_name',
      'status',
      'timestamp_utc',
      'blogger_post_id',
      'article_url',
      'image_sources',
      'publishing_mode',
      'main_keyword',
      'error_details',
    ];
    const escape = (v: string) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = filtered.map((r) =>
      [
        r.record_id,
        r.article_id,
        r.article_title,
        r.blog_id,
        r.blog_name,
        r.status,
        r.timestamp_utc,
        r.blogger_post_id,
        r.article_url,
        (r.image_sources || []).join('; '),
        r.publishing_mode,
        r.main_keyword,
        r.error_details,
      ]
        .map(escape)
        .join(',')
    );
    downloadFile([headers.join(','), ...rows].join('\n'), 'publishing-history.csv', 'text/csv;charset=utf-8');
  };

  const exportJson = () => {
    downloadFile(JSON.stringify(filtered, null, 2), 'publishing-history.json', 'application/json');
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input
            type="text"
            placeholder="Filter by keyword or title..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
          />
          <select
            aria-label="Filter by blog"
            value={blogFilter}
            onChange={(e) => setBlogFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="ALL">All Blogs</option>
            {blogs.map((b) => (
              <option key={b.blog_id} value={b.blog_id}>
                {b.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="ALL">All Statuses</option>
            <option value="Published">Published</option>
            <option value="Draft">Draft</option>
            <option value="Scheduled">Scheduled</option>
            <option value="Failed">Failed</option>
          </select>
          <select
            aria-label="Filter by publishing mode"
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="ALL">All Modes</option>
            <option value="manual">Manual</option>
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
            <option value="automatic">Automatic</option>
          </select>
          <input
            type="date"
            aria-label="Filter by UTC date"
            value={datePrefix}
            onChange={(e) => setDatePrefix(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
          />
        </div>

        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Showing <span className="font-semibold tabular-nums">{filtered.length}</span> of {history.length} records
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
            <button
              type="button"
              onClick={exportJson}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <Download className="h-3.5 w-3.5" /> Export JSON
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {filtered.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">No publishing history entries match your filters.</p>
        ) : (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-900/80">
                <th className="p-3">Article Title</th>
                <th className="p-3">Blog</th>
                <th className="p-3">Status</th>
                <th className="p-3">Mode</th>
                <th className="p-3">Post ID / URL</th>
                <th className="p-3">Image Sources</th>
                <th className="p-3">Date &amp; Time (UTC)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((rec) => (
                <tr key={rec.record_id}>
                  <td className="p-3">
                    <p className="font-medium text-slate-900 dark:text-slate-100">{rec.article_title}</p>
                    {rec.error_details && <p className="mt-0.5 text-red-600">{rec.error_details}</p>}
                  </td>
                  <td className="p-3">{rec.blog_name}</td>
                  <td className="p-3">
                    <StatusBadge status={rec.status} />
                  </td>
                  <td className="p-3 capitalize">{rec.publishing_mode}</td>
                  <td className="p-3 font-mono">
                    {rec.article_url ? (
                      <a
                        href={rec.article_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-brand-600 hover:underline"
                      >
                        {rec.blogger_post_id || 'View Post'}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      rec.blogger_post_id || '—'
                    )}
                  </td>
                  <td className="p-3">{(rec.image_sources || []).join(', ') || 'None'}</td>
                  <td className="p-3 tabular-nums text-slate-500">{rec.timestamp_utc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
