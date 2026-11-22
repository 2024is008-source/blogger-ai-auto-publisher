import React, { useMemo, useState } from 'react';
import { Check, Clock, Edit3, RotateCcw, Search, Send, Trash2, XCircle } from 'lucide-react';
import type { ArticleStatus, QueueItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface PublishingQueuePageProps {
  queue: QueueItem[];
  onEditArticle: (articleId: string) => void;
  onApprove: (queueId: string) => void;
  onCancel: (queueId: string) => void;
  onReschedule: (queueId: string, isoUtc: string) => void;
  onRetry: (queueId: string) => void;
  onDeleteDraft: (queueId: string) => void;
  onBulkPublish: (articleIds: string[], blogIds: string[]) => Promise<void>;
}

const ALL_STATUSES: ArticleStatus[] = [
  'Generated',
  'Editing',
  'Approved',
  'Draft',
  'Scheduled',
  'Publishing',
  'Published',
  'Failed',
  'Cancelled',
];

export const PublishingQueuePage: React.FC<PublishingQueuePageProps> = ({
  queue,
  onEditArticle,
  onApprove,
  onCancel,
  onReschedule,
  onRetry,
  onDeleteDraft,
  onBulkPublish,
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [rescheduleTarget, setRescheduleTarget] = useState<string | null>(null);
  const [rescheduleValue, setRescheduleValue] = useState('');

  const filtered = useMemo(() => {
    return queue.filter((item) => {
      if (statusFilter !== 'ALL' && item.status !== statusFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        return (
          item.title.toLowerCase().includes(q) ||
          item.target_blog_name.toLowerCase().includes(q) ||
          item.article_id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [queue, search, statusFilter]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleBulk = async () => {
    const selectedItems = queue.filter((q) => selectedIds.includes(q.queue_id));
    if (!selectedItems.length) return;
    const articleIds = Array.from(new Set(selectedItems.map((i) => i.article_id)));
    const blogIds = Array.from(new Set(selectedItems.map((i) => i.target_blog_id).filter(Boolean)));
    await onBulkPublish(articleIds, blogIds);
    setSelectedIds([]);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter queue..."
              className="h-9 rounded-lg border border-slate-300 bg-white pl-8 pr-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
          <select
            aria-label="Filter queue by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="ALL">All Statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {selectedIds.length > 0 && (
          <button
            type="button"
            onClick={handleBulk}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 text-xs font-medium text-white hover:bg-brand-700"
          >
            <Send className="h-3.5 w-3.5" />
            Bulk Publish Selected ({selectedIds.length})
          </button>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {filtered.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">No queue items match the current filter.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-900/80">
                <th className="p-3 w-8"></th>
                <th className="p-3">Article</th>
                <th className="p-3">Target Blog</th>
                <th className="p-3">Status</th>
                <th className="p-3">Scheduled (UTC)</th>
                <th className="p-3">Retries</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((item) => (
                <tr key={item.queue_id}>
                  <td className="p-3">
                    <input
                      type="checkbox"
                      aria-label={`Select ${item.title}`}
                      checked={selectedIds.includes(item.queue_id)}
                      onChange={() => toggleSelect(item.queue_id)}
                      className="h-4 w-4 rounded border-slate-300 text-brand-600"
                    />
                  </td>
                  <td className="p-3">
                    <p className="font-medium text-slate-900 dark:text-slate-100">{item.title}</p>
                    <p className="font-mono text-[11px] text-slate-500">{item.article_id}</p>
                    {item.error_message && (
                      <p className="mt-1 text-xs text-red-600 dark:text-red-400">{item.error_message}</p>
                    )}
                  </td>
                  <td className="p-3 text-xs text-slate-600 dark:text-slate-300">{item.target_blog_name}</td>
                  <td className="p-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="p-3 text-xs tabular-nums text-slate-500">
                    {rescheduleTarget === item.queue_id ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="datetime-local"
                          value={rescheduleValue}
                          onChange={(e) => setRescheduleValue(e.target.value)}
                          className="h-7 rounded border border-slate-300 px-1.5 text-xs dark:border-slate-700 dark:bg-slate-800"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            if (rescheduleValue) {
                              onReschedule(item.queue_id, new Date(rescheduleValue).toISOString());
                            }
                            setRescheduleTarget(null);
                          }}
                          className="rounded bg-brand-600 px-2 py-1 text-white"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      item.scheduled_at_utc || '—'
                    )}
                  </td>
                  <td className="p-3 text-xs tabular-nums">
                    {item.retry_count}/{item.max_retries}
                  </td>
                  <td className="p-3">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        title="Edit article"
                        aria-label="Edit article"
                        onClick={() => onEditArticle(item.article_id)}
                        className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800"
                      >
                        <Edit3 className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        title="Approve"
                        aria-label="Approve queued article"
                        onClick={() => onApprove(item.queue_id)}
                        className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        title="Reschedule"
                        aria-label="Change publication time"
                        onClick={() => {
                          setRescheduleTarget(item.queue_id);
                          setRescheduleValue('');
                        }}
                        className="rounded-md p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950"
                      >
                        <Clock className="h-4 w-4" />
                      </button>
                      {item.status === 'Failed' && (
                        <button
                          type="button"
                          title="Retry failed job"
                          aria-label="Retry failed article"
                          onClick={() => onRetry(item.queue_id)}
                          className="rounded-md p-1.5 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </button>
                      )}
                      {item.status === 'Scheduled' && (
                        <button
                          type="button"
                          title="Cancel schedule"
                          aria-label="Cancel scheduled article"
                          onClick={() => onCancel(item.queue_id)}
                          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                      {['Draft', 'Generated', 'Cancelled'].includes(item.status) && (
                        <button
                          type="button"
                          title="Delete unused draft"
                          aria-label="Delete unused draft"
                          onClick={() => onDeleteDraft(item.queue_id)}
                          className="rounded-md p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
