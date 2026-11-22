import React, { useMemo, useState } from 'react';
import { Activity, ExternalLink } from 'lucide-react';
import type { LogEntry, WorkflowRunSummary } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface LogsDiagnosticsPageProps {
  logs: LogEntry[];
  workflowRuns: WorkflowRunSummary[];
}

export const LogsDiagnosticsPage: React.FC<LogsDiagnosticsPageProps> = ({ logs, workflowRuns }) => {
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [query, setQuery] = useState('');

  const filteredLogs = useMemo(() => {
    return logs
      .filter((entry) => {
        if (levelFilter !== 'ALL' && entry.level !== levelFilter) return false;
        if (query.trim()) {
          const q = query.toLowerCase();
          return (
            entry.message.toLowerCase().includes(q) ||
            entry.component.toLowerCase().includes(q)
          );
        }
        return true;
      })
      .slice()
      .reverse();
  }, [logs, levelFilter, query]);

  return (
    <div className="space-y-6">
      {/* Workflow Diagnostics */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
          <Activity className="h-4 w-4 text-brand-600" />
          Recent GitHub Actions Runs
        </h2>
        {workflowRuns.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">
            No workflow runs loaded. Set your GitHub repository owner and name in Settings to inspect live runs.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 uppercase text-slate-500 dark:border-slate-800">
                  <th className="py-2 pr-3">Workflow</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Started</th>
                  <th className="py-2">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {workflowRuns.map((r) => (
                  <tr key={r.id}>
                    <td className="py-2 pr-3 font-medium">{r.name}</td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={r.conclusion || r.status} />
                    </td>
                    <td className="py-2 pr-3 tabular-nums text-slate-500">{r.created_at}</td>
                    <td className="py-2">
                      <a
                        href={r.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-brand-600 hover:underline"
                      >
                        GitHub Logs <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Structured Backend Logs */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Structured Application Logs (Secret-Redacted)
          </h2>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search component or message..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-800"
            />
            <select
              aria-label="Filter logs by level"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value as 'ALL' | 'INFO' | 'WARNING' | 'ERROR')}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="ALL">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>

        {filteredLogs.length === 0 ? (
          <p className="mt-4 text-xs text-slate-500">No structured log entries recorded in data/logs.json yet.</p>
        ) : (
          <div className="mt-3 max-h-[420px] space-y-2 overflow-y-auto font-mono text-xs">
            {filteredLogs.map((entry, idx) => (
              <div
                key={`${entry.timestamp}-${idx}`}
                className="rounded-lg border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-400">{entry.timestamp}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 font-semibold ${
                      entry.level === 'ERROR'
                        ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                        : entry.level === 'WARNING'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                    }`}
                  >
                    {entry.level}
                  </span>
                  <span className="text-brand-700 dark:text-brand-400">[{entry.component}]</span>
                </div>
                <p className="mt-1 text-slate-800 dark:text-slate-200">{entry.message}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
