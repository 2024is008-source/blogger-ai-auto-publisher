import React, { useState } from 'react';
import { ExternalLink, Globe, Plus, RefreshCw } from 'lucide-react';
import type { BlogAccount } from '../types';

interface BloggerAccountsPageProps {
  blogs: BlogAccount[];
  onAddBlog: (blog: BlogAccount) => void;
  onSyncBlogs: () => Promise<void>;
}

export const BloggerAccountsPage: React.FC<BloggerAccountsPageProps> = ({
  blogs,
  onAddBlog,
  onSyncBlogs,
}) => {
  const [blogId, setBlogId] = useState('');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [labels, setLabels] = useState('');
  const [maxDaily, setMaxDaily] = useState(3);
  const [syncing, setSyncing] = useState(false);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!blogId.trim() || !name.trim()) return;
    onAddBlog({
      blog_id: blogId.trim(),
      name: name.trim(),
      url: url.trim(),
      description: '',
      locale: 'en',
      default_labels: labels
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      default_timezone: 'UTC',
      max_daily_posts: maxDaily,
      active: true,
      last_synced_at: new Date().toISOString(),
    });
    setBlogId('');
    setName('');
    setUrl('');
    setLabels('');
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await onSyncBlogs();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Connected Blogger Websites ({blogs.length})
          </h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            OAuth 2.0 credentials live exclusively in GitHub Secrets. Sync retrieves your authorized blogs via Blogger API v3.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncing}
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-4 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
          Sync from Blogger API
        </button>
      </div>

      {/* Blog Cards */}
      {blogs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900">
          No Blogger websites registered in data/blogs.json yet. Run Sync from Blogger API or register a blog ID below.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {blogs.map((blog) => (
            <div
              key={blog.blog_id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                    <Globe className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{blog.name}</h3>
                    <p className="font-mono text-xs text-slate-500">ID: {blog.blog_id}</p>
                  </div>
                </div>
                {blog.url && (
                  <a
                    href={blog.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
                  >
                    Visit <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {blog.default_labels.map((lbl) => (
                  <span
                    key={lbl}
                    className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {lbl}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Max daily posts: <span className="font-semibold tabular-nums">{blog.max_daily_posts}</span> · Timezone: {blog.default_timezone}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Manual Register Form */}
      <form
        onSubmit={handleAdd}
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Add Blog Configuration (Non-Sensitive Metadata)
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <input
            type="text"
            required
            placeholder="Blogger Blog ID (numeric)"
            value={blogId}
            onChange={(e) => setBlogId(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <input
            type="text"
            required
            placeholder="Blog Display Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <input
            type="url"
            placeholder="https://yourblog.blogspot.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <input
            type="text"
            placeholder="Default labels (comma-separated)"
            value={labels}
            onChange={(e) => setLabels(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <input
            type="number"
            min={1}
            max={20}
            value={maxDaily}
            onChange={(e) => setMaxDaily(Number(e.target.value))}
            aria-label="Maximum daily posts"
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
        </div>
        <button
          type="submit"
          className="mt-4 inline-flex h-9 items-center gap-1.5 rounded-lg bg-navy-900 px-4 text-xs font-medium text-white hover:bg-slate-800 dark:bg-brand-600"
        >
          <Plus className="h-3.5 w-3.5" /> Add Blog
        </button>
      </form>
    </div>
  );
};
