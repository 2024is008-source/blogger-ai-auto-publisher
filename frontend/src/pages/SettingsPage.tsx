import React, { useState } from 'react';
import { Lock, Save, ShieldAlert } from 'lucide-react';
import type { AppSettings, LicenseFilter } from '../types';

interface SettingsPageProps {
  settings: AppSettings;
  sessionToken: string;
  onSaveSettings: (updated: AppSettings) => void;
  onSetSessionToken: (token: string) => void;
}

const REQUIRED_SECRETS = [
  'GEMINI_API_KEY',
  'GOOGLE_CLIENT_ID',
  'GOOGLE_CLIENT_SECRET',
  'BLOGGER_REFRESH_TOKEN',
  'BLOGGER_BLOG_ID',
  'OPENVERSE_ENABLED',
  'PEXELS_API_KEY',
  'PIXABAY_API_KEY',
  'SUPABASE_URL (optional)',
  'SUPABASE_SERVICE_ROLE_KEY (optional)',
];

export const SettingsPage: React.FC<SettingsPageProps> = ({
  settings,
  sessionToken,
  onSaveSettings,
  onSetSessionToken,
}) => {
  const [draft, setDraft] = useState<AppSettings>(settings);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          Repository &amp; Workflow Connection (Non-Sensitive)
        </h2>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              GitHub Owner / Username
            </label>
            <input
              type="text"
              value={draft.github_owner || ''}
              onChange={(e) => setDraft({ ...draft, github_owner: e.target.value })}
              placeholder="e.g., 2024is008-source"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Repository Name
            </label>
            <input
              type="text"
              value={draft.github_repo || ''}
              onChange={(e) => setDraft({ ...draft, github_repo: e.target.value })}
              placeholder="blogger-ai-auto-publisher"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Default Branch
            </label>
            <input
              type="text"
              value={draft.github_branch || 'main'}
              onChange={(e) => setDraft({ ...draft, github_branch: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
        </div>

        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/60 dark:bg-amber-950/30">
          <div className="flex items-start gap-2.5">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" />
            <div className="flex-1">
              <p className="text-xs font-semibold text-amber-900 dark:text-amber-200">
                Ephemeral Session Token for Workflow Dispatch (Memory Only)
              </p>
              <p className="mt-0.5 text-xs text-amber-800 dark:text-amber-300">
                Optional fine-grained GitHub PAT (Actions: Read &amp; Write) to trigger workflows directly from this tab. Never stored in localStorage, cookies, or repository files — cleared automatically on reload.
              </p>
              <input
                type="password"
                autoComplete="off"
                value={sessionToken}
                onChange={(e) => onSetSessionToken(e.target.value)}
                placeholder="github_pat_... (kept in RAM only)"
                className="mt-2 h-9 w-full max-w-md rounded-lg border border-amber-300 bg-white px-3 font-mono text-xs dark:border-amber-800 dark:bg-slate-900"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Model, SEO & Media Settings */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          AI Model, SEO Limits &amp; Image Hosting
        </h2>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Gemini Model Identifier (Configurable)
            </label>
            <input
              type="text"
              value={draft.gemini_model}
              onChange={(e) => setDraft({ ...draft, gemini_model: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Authorized Image Hosting Integration
            </label>
            <select
              value={draft.image_host_provider}
              onChange={(e) =>
                setDraft({ ...draft, image_host_provider: e.target.value as AppSettings['image_host_provider'] })
              }
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="none">Not configured (report missing host on upload)</option>
              <option value="cloudinary">Cloudinary (via GitHub Secrets)</option>
              <option value="github">GitHub Asset Repository (via GITHUB_TOKEN)</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
              Default License Filter
            </label>
            <select
              value={draft.default_license_filter}
              onChange={(e) => setDraft({ ...draft, default_license_filter: e.target.value as LicenseFilter })}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="cc0_public_domain">CC0 / Public Domain only</option>
              <option value="commercial_permitted">Commercial-use permitted</option>
              <option value="cc_with_attribution">Creative Commons with attribution</option>
              <option value="all_supported">All supported licenses</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Title Min / Max
              </label>
              <div className="flex gap-1.5">
                <input
                  type="number"
                  value={draft.seo_title_min}
                  onChange={(e) => setDraft({ ...draft, seo_title_min: Number(e.target.value) })}
                  className="h-10 w-full rounded-lg border border-slate-300 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                />
                <input
                  type="number"
                  value={draft.seo_title_max}
                  onChange={(e) => setDraft({ ...draft, seo_title_max: Number(e.target.value) })}
                  className="h-10 w-full rounded-lg border border-slate-300 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">
                Meta Min / Max
              </label>
              <div className="flex gap-1.5">
                <input
                  type="number"
                  value={draft.seo_meta_min}
                  onChange={(e) => setDraft({ ...draft, seo_meta_min: Number(e.target.value) })}
                  className="h-10 w-full rounded-lg border border-slate-300 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                />
                <input
                  type="number"
                  value={draft.seo_meta_max}
                  onChange={(e) => setDraft({ ...draft, seo_meta_max: Number(e.target.value) })}
                  className="h-10 w-full rounded-lg border border-slate-300 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                />
              </div>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onSaveSettings(draft)}
          className="mt-5 inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Save className="h-4 w-4" /> Save Non-Sensitive Settings
        </button>
      </div>

      {/* Required GitHub Secrets Reference */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
          <Lock className="h-4 w-4 text-brand-600" />
          GitHub Repository Secrets Reference
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Configure these variables under GitHub Repository &rarr; Settings &rarr; Secrets and variables &rarr; Actions. Never commit them into frontend code or public JSON files.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {REQUIRED_SECRETS.map((sec) => (
            <code
              key={sec}
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              {sec}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
};
