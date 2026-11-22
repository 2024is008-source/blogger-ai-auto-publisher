import React, { useMemo, useState } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Save, RefreshCw, Send, Tag } from 'lucide-react';
import type { AppSettings, Article, BlogAccount } from '../types';
import { RichTextEditor } from '../components/RichTextEditor';
import { analyzeArticleSEO } from '../services/seoAnalyzer';

interface ArticleEditorPageProps {
  articles: Article[];
  selectedArticleId: string | null;
  blogs: BlogAccount[];
  settings: AppSettings;
  onSelectArticle: (id: string) => void;
  onSaveArticle: (updated: Article) => void;
  onTriggerPublish: (article: Article, mode: 'draft' | 'manual') => void;
  onRegenerateArticle: (article: Article) => void;
  onRegenerateParagraph: (article: Article, selectedText: string) => void;
  onOpenImageFinder: () => void;
  onNotify: (type: 'success' | 'error' | 'info', title: string, detail?: string) => void;
}

export const ArticleEditorPage: React.FC<ArticleEditorPageProps> = ({
  articles,
  selectedArticleId,
  blogs,
  settings,
  onSelectArticle,
  onSaveArticle,
  onTriggerPublish,
  onRegenerateArticle,
  onRegenerateParagraph,
  onOpenImageFinder,
  onNotify,
}) => {
  const activeArticle = articles.find((a) => a.id === selectedArticleId) || articles[0] || null;
  const [labelInput, setLabelInput] = useState('');

  const seo = useMemo(() => {
    if (!activeArticle) return null;
    const otherTitles = articles.filter((a) => a.id !== activeArticle.id).map((a) => a.title);
    return analyzeArticleSEO(activeArticle, settings, otherTitles);
  }, [activeArticle, articles, settings]);

  if (!activeArticle) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          No articles available yet. Use the Article Generator to create your first draft.
        </p>
      </div>
    );
  }

  const updateField = <K extends keyof Article>(key: K, value: Article[K]) => {
    onSaveArticle({
      ...activeArticle,
      [key]: value,
      updated_at: new Date().toISOString(),
    });
  };

  const addLabel = () => {
    const clean = labelInput.trim();
    if (!clean || activeArticle.labels.includes(clean)) return;
    updateField('labels', [...activeArticle.labels, clean]);
    setLabelInput('');
  };

  const removeLabel = (lbl: string) => {
    updateField(
      'labels',
      activeArticle.labels.filter((item) => item !== lbl)
    );
  };

  const handleCopyHtml = async () => {
    try {
      await navigator.clipboard.writeText(activeArticle.html_content);
      onNotify('success', 'HTML copied to clipboard');
    } catch {
      onNotify('error', 'Clipboard copy failed', 'Copy directly from the HTML tab.');
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      {/* Left 2 Columns: Metadata + RichTextEditor */}
      <div className="space-y-4 xl:col-span-2">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <select
            aria-label="Select article to edit"
            value={activeArticle.id}
            onChange={(e) => onSelectArticle(e.target.value)}
            className="h-9 max-w-md flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          >
            {articles.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title} ({a.status})
              </option>
            ))}
          </select>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onNotify('success', 'Draft saved locally', 'Commit or dispatch publish workflow when ready.')}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <Save className="h-3.5 w-3.5" /> Save Draft
            </button>
            <button
              type="button"
              onClick={() => onRegenerateArticle(activeArticle)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Regenerate Full
            </button>
            <button
              type="button"
              onClick={() => onTriggerPublish(activeArticle, 'draft')}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-navy-900 px-3 text-xs font-medium text-white hover:bg-slate-800 dark:bg-slate-700"
            >
              Push Blogger Draft
            </button>
            <button
              type="button"
              onClick={() => onTriggerPublish(activeArticle, 'manual')}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-xs font-medium text-white hover:bg-brand-700"
            >
              <Send className="h-3.5 w-3.5" /> Publish
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Article Title ({activeArticle.title.length} chars)
            </label>
            <input
              type="text"
              value={activeArticle.title}
              onChange={(e) => updateField('title', e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              SEO Slug
            </label>
            <input
              type="text"
              value={activeArticle.slug}
              onChange={(e) => updateField('slug', e.target.value)}
              className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Target Blog
            </label>
            <select
              value={activeArticle.blog_id}
              onChange={(e) => updateField('blog_id', e.target.value)}
              className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="">Default Blog Secret</option>
              {blogs.map((b) => (
                <option key={b.blog_id} value={b.blog_id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Meta Description ({activeArticle.meta_description.length} chars)
            </label>
            <textarea
              rows={2}
              value={activeArticle.meta_description}
              onChange={(e) => updateField('meta_description', e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Blogger Labels
            </label>
            <div className="flex flex-wrap items-center gap-1.5">
              {activeArticle.labels.map((lbl) => (
                <span
                  key={lbl}
                  className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  <Tag className="h-3 w-3" />
                  {lbl}
                  <button
                    type="button"
                    onClick={() => removeLabel(lbl)}
                    aria-label={`Remove label ${lbl}`}
                    className="ml-0.5 text-slate-400 hover:text-red-500"
                  >
                    ×
                  </button>
                </span>
              ))}
              <input
                type="text"
                value={labelInput}
                onChange={(e) => setLabelInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addLabel();
                  }
                }}
                placeholder="Add label + Enter"
                className="h-7 rounded-md border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-800"
              />
            </div>
          </div>
        </div>

        <RichTextEditor
          value={activeArticle.html_content}
          onChange={(html) => updateField('html_content', html)}
          onCopyHtml={handleCopyHtml}
          onOpenImagePicker={onOpenImageFinder}
          onRegenerateParagraph={(sel) => onRegenerateParagraph(activeArticle, sel)}
        />
      </div>

      {/* Right Column: Live SEO Diagnostics */}
      <aside className="space-y-4">
        {seo && (
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                On-Page SEO Analysis
              </h2>
              <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-sm font-bold tabular-nums text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                {seo.score}/100
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              {seo.disclaimer}
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-2.5 text-center text-xs dark:bg-slate-800/70">
              <div>
                <p className="text-slate-500">Words</p>
                <p className="font-semibold tabular-nums">{seo.word_count}</p>
              </div>
              <div>
                <p className="text-slate-500">H2 / H3</p>
                <p className="font-semibold tabular-nums">
                  {seo.heading_counts.h2}/{seo.heading_counts.h3}
                </p>
              </div>
              <div>
                <p className="text-slate-500">Grade</p>
                <p className="font-semibold tabular-nums">{seo.readability_grade}</p>
              </div>
            </div>

            <ul className="mt-4 space-y-2.5">
              {seo.checks.map((c) => (
                <li key={c.check} className="rounded-lg border border-slate-100 p-2.5 text-xs dark:border-slate-800">
                  <div className="flex items-start gap-2">
                    {c.status === 'pass' && <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />}
                    {c.status === 'warning' && <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />}
                    {c.status === 'fail' && <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" />}
                    <div>
                      <p className="font-medium text-slate-900 dark:text-slate-100">{c.check}</p>
                      <p className="text-slate-600 dark:text-slate-400">{c.message}</p>
                      {c.recommendation && (
                        <p className="mt-1 text-brand-700 dark:text-brand-400">{c.recommendation}</p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
};
