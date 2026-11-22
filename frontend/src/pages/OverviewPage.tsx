import React from 'react';
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  FileEdit,
  FileText,
  Globe,
  Workflow,
} from 'lucide-react';
import type {
  Article,
  BlogAccount,
  PublishingHistoryRecord,
  QueueItem,
  WorkflowRunSummary,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface OverviewPageProps {
  articles: Article[];
  blogs: BlogAccount[];
  queue: QueueItem[];
  history: PublishingHistoryRecord[];
  workflowRuns: WorkflowRunSummary[];
  onOpenGenerator: () => void;
  onEditArticle: (articleId: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  articles,
  blogs,
  queue,
  history,
  workflowRuns,
  onOpenGenerator,
  onEditArticle,
}) => {
  const totalGenerated = articles.length;
  const totalPublished = history.filter((h) => h.status === 'Published').length;
  const draftCount =
    articles.filter((a) => a.status === 'Draft' || a.status === 'Generated' || a.status === 'Editing').length;
  const scheduledCount = queue.filter((q) => q.status === 'Scheduled').length;
  const failedCount =
    history.filter((h) => h.status === 'Failed').length +
    queue.filter((q) => q.status === 'Failed').length;
  const connectedBlogs = blogs.filter((b) => b.active).length;

  const upcoming = queue
    .filter((q) => q.status === 'Scheduled' && q.scheduled_at_utc)
    .sort((a, b) => (a.scheduled_at_utc || '').localeCompare(b.scheduled_at_utc || ''))
    .slice(0, 5);

  const kpis = [
    { label: 'Articles Generated', value: totalGenerated, icon: FileText, tone: 'text-slate-700 dark:text-slate-200' },
    { label: 'Published Articles', value: totalPublished, icon: CheckCircle2, tone: 'text-emerald-700 dark:text-emerald-400' },
    { label: 'Draft & Editing', value: draftCount, icon: FileEdit, tone: 'text-amber-700 dark:text-amber-400' },
    { label: 'Scheduled Posts', value: scheduledCount, icon: CalendarClock, tone: 'text-blue-700 dark:text-blue-400' },
    { label: 'Failed Attempts', value: failedCount, icon: AlertCircle, tone: 'text-red-700 dark:text-red-400' },
    { label: 'Connected Blogs', value: connectedBlogs, icon: Globe, tone: 'text-brand-700 dark:text-brand-400' },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.label}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {kpi.label}
                </p>
                <Icon className={`h-4 w-4 ${kpi.tone}`} />
              </div>
              <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">
                {kpi.value}
              </p>
            </div>
          );
        })}
      </div>

      {/* Main Two-Column Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Upcoming Scheduled Posts */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Upcoming Scheduled Posts
            </h2>
            <button
              type="button"
              onClick={onOpenGenerator}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
            >
              New Article
            </button>
          </div>
          {upcoming.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              No scheduled posts in the repository queue yet.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
              {upcoming.map((item) => (
                <li key={item.queue_id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <button
                      type="button"
                      onClick={() => onEditArticle(item.article_id)}
                      className="truncate text-left text-sm font-medium text-slate-900 hover:text-brand-600 dark:text-slate-100"
                    >
                      {item.title}
                    </button>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {item.target_blog_name} · {item.scheduled_at_utc}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* GitHub Actions Workflow Status */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <Workflow className="h-4 w-4 text-brand-600" />
              GitHub Actions Workflow Status
            </h2>
          </div>
          {workflowRuns.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              Configure your GitHub repository owner and name in Settings to display live GitHub Actions workflow runs.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
              {workflowRuns.slice(0, 6).map((run) => (
                <li key={run.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <a
                      href={run.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 truncate text-sm font-medium text-slate-900 hover:text-brand-600 dark:text-slate-100"
                    >
                      {run.name}
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(run.created_at).toLocaleString()}
                    </p>
                  </div>
                  <StatusBadge status={run.conclusion || run.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Recent Publishing Activity */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Recent Activity</h2>
        {history.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            No publishing history recorded yet. Published posts, drafts, and errors from GitHub Actions will appear here automatically.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <th className="py-2.5 pr-4">Article</th>
                  <th className="py-2.5 pr-4">Blog</th>
                  <th className="py-2.5 pr-4">Mode</th>
                  <th className="py-2.5 pr-4">Status</th>
                  <th className="py-2.5">UTC Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {history.slice(0, 8).map((rec) => (
                  <tr key={rec.record_id}>
                    <td className="py-2.5 pr-4 font-medium text-slate-900 dark:text-slate-100">
                      {rec.article_url ? (
                        <a
                          href={rec.article_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-brand-600 hover:underline"
                        >
                          {rec.article_title}
                        </a>
                      ) : (
                        rec.article_title
                      )}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-600 dark:text-slate-300">{rec.blog_name}</td>
                    <td className="py-2.5 pr-4 capitalize text-slate-600 dark:text-slate-300">{rec.publishing_mode}</td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={rec.status} />
                    </td>
                    <td className="py-2.5 tabular-nums text-xs text-slate-500 dark:text-slate-400">
                      {rec.timestamp_utc}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
