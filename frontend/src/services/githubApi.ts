import type {
  AppSettings,
  Article,
  BlogAccount,
  ImageAsset,
  LicenseFilter,
  LogEntry,
  PublishingHistoryRecord,
  QueueItem,
  ScheduleConfig,
  WorkflowRunSummary,
} from '../types';

export interface GitHubRepoConfig {
  owner: string;
  repo: string;
  branch: string;
  /** Ephemeral in-memory PAT for triggering workflow_dispatch or committing non-secret data edits. Never persisted to localStorage. */
  sessionToken?: string;
}

async function fetchJsonSafe<T>(url: string, headers?: Record<string, string>, fallback?: T): Promise<T> {
  try {
    const res = await fetch(url, { headers });
    if (!res.ok) {
      if (fallback !== undefined) return fallback;
      throw new Error(`HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (fallback !== undefined) return fallback;
    throw err;
  }
}

export async function loadRepositorySnapshot(cfg: GitHubRepoConfig | null): Promise<{
  articles: Article[];
  blogs: BlogAccount[];
  queue: QueueItem[];
  history: PublishingHistoryRecord[];
  licenses: ImageAsset[];
  schedule: ScheduleConfig;
  settings: AppSettings;
  logs: LogEntry[];
}> {
  const defaultSchedule: ScheduleConfig = {
    enabled: false,
    frequency: 'daily',
    days_of_week: ['Mon', 'Wed', 'Fri'],
    preferred_time_local: '09:00',
    timezone_name: 'UTC',
    max_daily_posts: 2,
    target_blog_ids: [],
  };

  const defaultSettings: AppSettings = {
    gemini_model: 'gemini-2.5-flash',
    seo_title_min: 45,
    seo_title_max: 65,
    seo_meta_min: 120,
    seo_meta_max: 160,
    default_license_filter: 'commercial_permitted',
    default_timezone: 'UTC',
    image_host_provider: 'none',
    github_owner: cfg?.owner || '',
    github_repo: cfg?.repo || '',
    github_branch: cfg?.branch || 'main',
  };

  const baseRaw =
    cfg && cfg.owner && cfg.repo
      ? `https://raw.githubusercontent.com/${encodeURIComponent(cfg.owner)}/${encodeURIComponent(cfg.repo)}/${encodeURIComponent(cfg.branch || 'main')}/data`
      : './data';

  const [blogs, queue, history, licenses, schedule, settings, logs, articlesIndex] = await Promise.all([
    fetchJsonSafe<BlogAccount[]>(`${baseRaw}/blogs.json`, undefined, []),
    fetchJsonSafe<QueueItem[]>(`${baseRaw}/queue.json`, undefined, []),
    fetchJsonSafe<PublishingHistoryRecord[]>(`${baseRaw}/publishing-history/history.json`, undefined, []),
    fetchJsonSafe<ImageAsset[]>(`${baseRaw}/image-licenses/licenses.json`, undefined, []),
    fetchJsonSafe<ScheduleConfig>(`${baseRaw}/schedule-config.json`, undefined, defaultSchedule),
    fetchJsonSafe<AppSettings>(`${baseRaw}/settings.json`, undefined, defaultSettings),
    fetchJsonSafe<LogEntry[]>(`${baseRaw}/logs.json`, undefined, []),
    fetchJsonSafe<string[]>(`${baseRaw}/articles/index.json`, undefined, []),
  ]);

  const articles: Article[] = [];
  if (Array.isArray(articlesIndex) && articlesIndex.length > 0) {
    const loaded = await Promise.all(
      articlesIndex.map((id) =>
        fetchJsonSafe<Article | null>(`${baseRaw}/articles/${encodeURIComponent(id)}.json`, undefined, null)
      )
    );
    for (const art of loaded) {
      if (art && art.id) articles.push(art);
    }
  } else if (cfg && cfg.owner && cfg.repo) {
    const headers: Record<string, string> = { Accept: 'application/vnd.github+json' };
    if (cfg.sessionToken) headers.Authorization = `Bearer ${cfg.sessionToken}`;
    const files = await fetchJsonSafe<Array<{ name: string; download_url?: string }>>(
      `https://api.github.com/repos/${encodeURIComponent(cfg.owner)}/${encodeURIComponent(cfg.repo)}/contents/data/articles?ref=${encodeURIComponent(cfg.branch || 'main')}`,
      headers,
      []
    );
    const jsonFiles = files.filter((f) => f.name.endsWith('.json') && f.name !== 'index.json' && f.download_url);
    const loaded = await Promise.all(
      jsonFiles.map((f) => fetchJsonSafe<Article | null>(f.download_url as string, undefined, null))
    );
    for (const art of loaded) {
      if (art && art.id) articles.push(art);
    }
  }

  return {
    articles,
    blogs,
    queue,
    history,
    licenses,
    schedule: { ...defaultSchedule, ...schedule },
    settings: { ...defaultSettings, ...settings },
    logs,
  };
}

export async function fetchWorkflowRuns(cfg: GitHubRepoConfig): Promise<WorkflowRunSummary[]> {
  if (!cfg.owner || !cfg.repo) return [];
  const headers: Record<string, string> = { Accept: 'application/vnd.github+json' };
  if (cfg.sessionToken) headers.Authorization = `Bearer ${cfg.sessionToken}`;
  const data = await fetchJsonSafe<{ workflow_runs?: WorkflowRunSummary[] }>(
    `https://api.github.com/repos/${encodeURIComponent(cfg.owner)}/${encodeURIComponent(cfg.repo)}/actions/runs?per_page=10`,
    headers,
    { workflow_runs: [] }
  );
  return data.workflow_runs || [];
}

export async function triggerGitHubWorkflow(
  cfg: GitHubRepoConfig,
  workflowFile: string,
  inputs: Record<string, string>
): Promise<void> {
  if (!cfg.owner || !cfg.repo) {
    throw new Error('Configure your GitHub Repository Owner and Name in Settings first.');
  }
  if (!cfg.sessionToken) {
    throw new Error(
      'Enter an ephemeral GitHub Personal Access Token (Actions: write) in Settings to dispatch workflows directly from this session.'
    );
  }
  const url = `https://api.github.com/repos/${encodeURIComponent(cfg.owner)}/${encodeURIComponent(cfg.repo)}/actions/workflows/${encodeURIComponent(workflowFile)}/dispatches`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${cfg.sessionToken}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ref: cfg.branch || 'main',
      inputs,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub Actions dispatch failed (HTTP ${res.status}): ${text.slice(0, 200)}`);
  }
}

export async function searchPublicImages(
  query: string,
  licenseFilter: LicenseFilter
): Promise<ImageAsset[]> {
  const results: ImageAsset[] = [];
  const q = query.trim();
  if (!q) return [];

  // 1. Openverse public API (no key required)
  try {
    const ovRes = await fetch(
      `https://api.openverse.org/v1/images/?q=${encodeURIComponent(q)}&page_size=10`
    );
    if (ovRes.ok) {
      const data = await ovRes.json();
      for (const item of data.results || []) {
        const lic = String(item.license || '').toLowerCase();
        const isPublicDomain = lic === 'cc0' || lic === 'pdm';
        const isCommercial = !lic.includes('nc');
        if (licenseFilter === 'cc0_public_domain' && !isPublicDomain) continue;
        if (licenseFilter === 'commercial_permitted' && !isCommercial) continue;
        const licenseName = isPublicDomain
          ? 'CC0 1.0 Public Domain'
          : `CC ${lic.toUpperCase()} ${item.license_version || ''}`.trim();
        const creator = item.creator || 'Unknown creator';
        const title = item.title || q;
        const licenseUrl = item.license_url || 'https://creativecommons.org/licenses/';
        results.push({
          id: String(item.id),
          title,
          original_url: item.url,
          preview_url: item.thumbnail || item.url,
          creator_name: creator,
          source_provider: 'Openverse',
          license_name: licenseName,
          license_url: licenseUrl,
          attribution_required: !isPublicDomain,
          attribution_text: isPublicDomain
            ? `Photo: ${title} by ${creator} (Openverse, ${licenseName})`
            : `"${title}" by ${creator} via Openverse, licensed under ${licenseName} (${licenseUrl})`,
          retrieval_date: new Date().toISOString(),
          commercial_use_permitted: isCommercial,
          hosted_url: '',
          alt_text: title,
          width: item.width ?? null,
          height: item.height ?? null,
        });
      }
    }
  } catch {
    // Continue to Wikimedia Commons if Openverse is unreachable
  }

  // 2. Wikimedia Commons public API (CORS enabled with origin=*)
  try {
    const wmUrl =
      `https://commons.wikimedia.org/w/api.php?action=query&format=json&origin=*` +
      `&generator=search&gsrsearch=${encodeURIComponent(`filetype:bitmap ${q}`)}` +
      `&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=640`;
    const wmRes = await fetch(wmUrl);
    if (wmRes.ok) {
      const data = await wmRes.json();
      const pages = Object.values((data.query && data.query.pages) || {}) as Array<Record<string, unknown>>;
      for (const page of pages) {
        const infos = (page.imageinfo as Array<Record<string, unknown>>) || [];
        if (!infos.length) continue;
        const info = infos[0];
        const ext = (info.extmetadata as Record<string, { value?: string }>) || {};
        const rawLic = (ext.LicenseShortName?.value || '').replace(/<[^>]+>/g, '').trim();
        if (!rawLic) continue;
        const lowerLic = rawLic.toLowerCase();
        const isPublicDomain = lowerLic.includes('cc0') || lowerLic.includes('public domain') || lowerLic.startsWith('pd');
        const isCC = lowerLic.includes('cc') || isPublicDomain;
        const isCommercial = isCC && !lowerLic.includes('nc');
        if (!isCC) continue;
        if (licenseFilter === 'cc0_public_domain' && !isPublicDomain) continue;
        if (licenseFilter === 'commercial_permitted' && !isCommercial) continue;

        const creator = (ext.Artist?.value || 'Wikimedia Contributor').replace(/<[^>]+>/g, '').trim();
        const title =
          (ext.ObjectName?.value || String(page.title || q).replace(/^File:/, '')).replace(/<[^>]+>/g, '').trim();
        const licenseUrl = (ext.LicenseUrl?.value || 'https://creativecommons.org/licenses/').trim();

        results.push({
          id: String(page.pageid || info.url),
          title,
          original_url: String(info.url || ''),
          preview_url: String(info.thumburl || info.url || ''),
          creator_name: creator,
          source_provider: 'Wikimedia Commons',
          license_name: rawLic,
          license_url: licenseUrl,
          attribution_required: !isPublicDomain,
          attribution_text: isPublicDomain
            ? `Photo: ${title} by ${creator} (Wikimedia Commons, ${rawLic})`
            : `"${title}" by ${creator} via Wikimedia Commons, licensed under ${rawLic} (${licenseUrl})`,
          retrieval_date: new Date().toISOString(),
          commercial_use_permitted: isCommercial,
          hosted_url: '',
          alt_text: title,
          width: (info.width as number) ?? null,
          height: (info.height as number) ?? null,
        });
      }
    }
  } catch {
    // Graceful degradation
  }

  return results;
}
