import React, { useState } from 'react';
import { CalendarClock, Play, Save } from 'lucide-react';
import type { BlogAccount, ScheduleConfig } from '../types';

interface AutomationSchedulerPageProps {
  schedule: ScheduleConfig;
  blogs: BlogAccount[];
  onSaveSchedule: (updated: ScheduleConfig) => void;
  onRunQueueNow: () => Promise<void>;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Colombo',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
];

export const AutomationSchedulerPage: React.FC<AutomationSchedulerPageProps> = ({
  schedule,
  blogs,
  onSaveSchedule,
  onRunQueueNow,
}) => {
  const [draft, setDraft] = useState<ScheduleConfig>(schedule);
  const [running, setRunning] = useState(false);

  const toggleDay = (day: string) => {
    setDraft((prev) => ({
      ...prev,
      days_of_week: prev.days_of_week.includes(day)
        ? prev.days_of_week.filter((d) => d !== day)
        : [...prev.days_of_week, day],
    }));
  };

  const toggleBlog = (blogId: string) => {
    setDraft((prev) => ({
      ...prev,
      target_blog_ids: prev.target_blog_ids.includes(blogId)
        ? prev.target_blog_ids.filter((b) => b !== blogId)
        : [...prev.target_blog_ids, blogId],
    }));
  };

  const handleRunNow = async () => {
    setRunning(true);
    try {
      await onRunQueueNow();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <CalendarClock className="h-5 w-5 text-brand-600" />
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                GitHub Actions Automation Scheduler
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                All timestamps are stored internally in UTC. Because GitHub Actions cron may drift by several minutes, the queue processor publishes every due job where scheduled_at_utc &lt;= now_utc up to your daily cap.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRunNow}
            disabled={running}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-navy-900 px-4 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-brand-600"
          >
            <Play className="h-3.5 w-3.5" />
            {running ? 'Dispatching...' : 'Run Queue Processor Now'}
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex items-center gap-2.5 text-sm font-medium text-slate-800 dark:text-slate-200 md:col-span-2">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-brand-600"
            />
            Enable automated scheduled queue publishing
          </label>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Publishing Frequency
            </label>
            <select
              value={draft.frequency}
              onChange={(e) => setDraft({ ...draft, frequency: e.target.value as ScheduleConfig['frequency'] })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="custom">Custom Days</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Preferred Local Publishing Time
            </label>
            <input
              type="time"
              value={draft.preferred_time_local}
              onChange={(e) => setDraft({ ...draft, preferred_time_local: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Timezone
            </label>
            <select
              value={draft.timezone_name}
              onChange={(e) => setDraft({ ...draft, timezone_name: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Maximum Daily Posts
            </label>
            <input
              type="number"
              min={1}
              max={25}
              value={draft.max_daily_posts}
              onChange={(e) => setDraft({ ...draft, max_daily_posts: Number(e.target.value) })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div className="md:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Days of the Week
            </label>
            <div className="flex flex-wrap gap-2">
              {DAYS.map((day) => {
                const active = draft.days_of_week.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    onClick={() => toggleDay(day)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                      active
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
          </div>

          {blogs.length > 0 && (
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Target Blogs for Automated Publishing
              </label>
              <div className="flex flex-wrap gap-2">
                {blogs.map((b) => {
                  const selected = draft.target_blog_ids.includes(b.blog_id);
                  return (
                    <button
                      key={b.blog_id}
                      type="button"
                      onClick={() => toggleBlog(b.blog_id)}
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                        selected
                          ? 'border-brand-600 bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
                          : 'border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}
                    >
                      {b.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="mt-6">
          <button
            type="button"
            onClick={() => onSaveSchedule(draft)}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700"
          >
            <Save className="h-4 w-4" /> Save Schedule Configuration
          </button>
        </div>
      </div>
    </div>
  );
};
