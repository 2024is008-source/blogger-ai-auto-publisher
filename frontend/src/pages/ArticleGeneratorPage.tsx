import React, { useState } from 'react';
import { Loader2, Send, Sparkles } from 'lucide-react';
import type { Article, BlogAccount, PublishingMode } from '../types';

interface ArticleGeneratorPageProps {
  blogs: BlogAccount[];
  defaultTimezone: string;
  geminiModel: string;
  onDispatchGenerate: (inputs: Record<string, string>) => Promise<void>;
  onCreateLocalDraft: (article: Article) => void;
}

const TEMPLATES = [
  { value: 'informational_guide', label: 'Informational Guide' },
  { value: 'how_to_tutorial', label: 'How-to Tutorial' },
  { value: 'listicle', label: 'Listicle' },
  { value: 'product_comparison', label: 'Product Comparison' },
  { value: 'beginner_guide', label: 'Beginner Guide' },
  { value: 'news_article', label: 'News Article' },
  { value: 'home_and_lifestyle', label: 'Home & Lifestyle Article' },
];

export const ArticleGeneratorPage: React.FC<ArticleGeneratorPageProps> = ({
  blogs,
  defaultTimezone,
  geminiModel,
  onDispatchGenerate,
  onCreateLocalDraft,
}) => {
  const [mainKeyword, setMainKeyword] = useState('');
  const [articleTitle, setArticleTitle] = useState('');
  const [secondaryKeywords, setSecondaryKeywords] = useState('');
  const [targetCountry, setTargetCountry] = useState('United States');
  const [targetAudience, setTargetAudience] = useState('General readers');
  const [language, setLanguage] = useState('English');
  const [writingStyle, setWritingStyle] = useState('Informative and practical');
  const [articleLength, setArticleLength] = useState<'short' | 'medium' | 'long'>('medium');
  const [numSections, setNumSections] = useState(5);
  const [numImages, setNumImages] = useState(2);
  const [blogId, setBlogId] = useState(blogs[0]?.blog_id || '');
  const [template, setTemplate] = useState('informational_guide');
  const [publishingMode, setPublishingMode] = useState<PublishingMode>('draft');
  const [scheduledTime, setScheduledTime] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mainKeyword.trim()) return;
    setSubmitting(true);
    try {
      await onDispatchGenerate({
        topic: mainKeyword.trim(),
        title: articleTitle.trim(),
        secondary_keywords: secondaryKeywords.trim(),
        target_country: targetCountry,
        target_audience: targetAudience,
        language,
        writing_style: writingStyle,
        article_length: articleLength,
        num_sections: String(numSections),
        num_images: String(numImages),
        target_blog_id: blogId,
        template,
        publishing_mode: publishingMode,
        scheduled_time: scheduledTime,
        timezone: defaultTimezone,
        fetch_images: numImages > 0 ? 'true' : 'false',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateDraftNow = () => {
    if (!mainKeyword.trim()) return;
    const title = articleTitle.trim() || `${mainKeyword.trim()} — Complete Guide`;
    const slug = title
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .slice(0, 65);
    const now = new Date().toISOString();
    const draft: Article = {
      id: `art_${Date.now().toString(36)}`,
      title,
      suggested_titles: [title],
      slug: slug || 'draft-article',
      meta_description: `Practical guide covering ${mainKeyword.trim()} for ${targetAudience.toLowerCase()} in ${targetCountry}.`,
      main_keyword: mainKeyword.trim(),
      secondary_keywords: secondaryKeywords
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      labels: [mainKeyword.trim()],
      outline: ['Introduction', 'Core Concepts', 'Step-by-Step Approach', 'Common Pitfalls', 'Conclusion'],
      html_content: `<p>This working draft introduces <strong>${mainKeyword.trim()}</strong> for ${targetAudience}.</p><h2>Understanding ${mainKeyword.trim()}</h2><p>Outline your key definitions and practical context here.</p><h2>Actionable Steps</h2><ul><li>Step 1: Define your objective.</li><li>Step 2: Apply verified best practices.</li></ul><h2>Conclusion</h2><p>Summarize practical next steps for the reader.</p>`,
      image_keywords: [mainKeyword.trim()],
      image_alt_texts: [`Illustration of ${mainKeyword.trim()}`],
      images: [],
      template,
      language,
      target_country: targetCountry,
      target_audience: targetAudience,
      blog_id: blogId,
      status: 'Editing',
      seo_analysis: null,
      created_at: now,
      updated_at: now,
    };
    onCreateLocalDraft(draft);
  };

  return (
    <form onSubmit={handleDispatch} className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Gemini AI Article Generator
            </h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Configured model: <span className="font-mono font-medium">{geminiModel}</span> · Executes securely inside GitHub Actions using GitHub Secrets.
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Main Keyword *
            </label>
            <input
              type="text"
              required
              value={mainKeyword}
              onChange={(e) => setMainKeyword(e.target.value)}
              placeholder="e.g., indoor herb gardening for beginners"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Article Title (optional — Gemini suggests titles if blank)
            </label>
            <input
              type="text"
              value={articleTitle}
              onChange={(e) => setArticleTitle(e.target.value)}
              placeholder="Leave empty for AI-generated SEO title"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div className="md:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Secondary Keywords (comma-separated)
            </label>
            <input
              type="text"
              value={secondaryKeywords}
              onChange={(e) => setSecondaryKeywords(e.target.value)}
              placeholder="windowsill herbs, potting soil mix, basil care"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Article Template
            </label>
            <select
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              {TEMPLATES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Target Website / Blog
            </label>
            <select
              value={blogId}
              onChange={(e) => setBlogId(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="">Default BLOGGER_BLOG_ID secret</option>
              {blogs.map((b) => (
                <option key={b.blog_id} value={b.blog_id}>
                  {b.name} ({b.blog_id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Target Country
            </label>
            <input
              type="text"
              value={targetCountry}
              onChange={(e) => setTargetCountry(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Target Audience
            </label>
            <input
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Language
            </label>
            <input
              type="text"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Writing Style
            </label>
            <input
              type="text"
              value={writingStyle}
              onChange={(e) => setWritingStyle(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Article Length
            </label>
            <select
              value={articleLength}
              onChange={(e) => setArticleLength(e.target.value as 'short' | 'medium' | 'long')}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="short">Short (~800 words)</option>
              <option value="medium">Medium (~1,400 words)</option>
              <option value="long">Long (~2,200 words)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Sections (H2)
              </label>
              <input
                type="number"
                min={2}
                max={12}
                value={numSections}
                onChange={(e) => setNumSections(Number(e.target.value))}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Images
              </label>
              <input
                type="number"
                min={0}
                max={6}
                value={numImages}
                onChange={(e) => setNumImages(Number(e.target.value))}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Publishing Mode
            </label>
            <select
              value={publishingMode}
              onChange={(e) => setPublishingMode(e.target.value as PublishingMode)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="draft">Save as Draft (Recommended)</option>
              <option value="manual">Queue for Manual Approval</option>
              <option value="scheduled">Scheduled Publication</option>
              <option value="automatic">Automatic Publishing</option>
            </select>
          </div>

          {publishingMode === 'scheduled' && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Scheduled Local Time ({defaultTimezone})
              </label>
              <input
                type="datetime-local"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
              />
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={submitting || !mainKeyword.trim()}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate via GitHub Actions
          </button>
          <button
            type="button"
            onClick={handleCreateDraftNow}
            disabled={!mainKeyword.trim()}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <Send className="h-4 w-4" />
            Open Working Draft in Editor
          </button>
        </div>
      </div>
    </form>
  );
};
