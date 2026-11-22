import React, { useCallback, useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { ToastContainer } from './components/ToastContainer';
import { ConfirmDialog } from './components/ConfirmDialog';
import { useTheme } from './hooks/useTheme';
import { useNotifications } from './hooks/useNotifications';
import {
  fetchWorkflowRuns,
  loadRepositorySnapshot,
  triggerGitHubWorkflow,
  type GitHubRepoConfig,
} from './services/githubApi';
import type {
  AppSettings,
  Article,
  BlogAccount,
  ImageAsset,
  LogEntry,
  NavSection,
  PublishingHistoryRecord,
  QueueItem,
  ScheduleConfig,
  WorkflowRunSummary,
} from './types';
import { OverviewPage } from './pages/OverviewPage';
import { ArticleGeneratorPage } from './pages/ArticleGeneratorPage';
import { ArticleEditorPage } from './pages/ArticleEditorPage';
import { ImageFinderPage } from './pages/ImageFinderPage';
import { BloggerAccountsPage } from './pages/BloggerAccountsPage';
import { PublishingQueuePage } from './pages/PublishingQueuePage';
import { PublishingHistoryPage } from './pages/PublishingHistoryPage';
import { AutomationSchedulerPage } from './pages/AutomationSchedulerPage';
import { SettingsPage } from './pages/SettingsPage';
import { LogsDiagnosticsPage } from './pages/LogsDiagnosticsPage';

export const App: React.FC = () => {
  const { dark, toggleTheme } = useTheme();
  const { toasts, notify, dismiss } = useNotifications();

  const [active, setActive] = useState<NavSection>('overview');
  const [loading, setLoading] = useState(false);

  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [blogs, setBlogs] = useState<BlogAccount[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [history, setHistory] = useState<PublishingHistoryRecord[]>([]);
  const [licenses, setLicenses] = useState<ImageAsset[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunSummary[]>([]);
  const [schedule, setSchedule] = useState<ScheduleConfig>({
    enabled: false,
    frequency: 'daily',
    days_of_week: ['Mon', 'Wed', 'Fri'],
    preferred_time_local: '09:00',
    timezone_name: 'UTC',
    max_daily_posts: 2,
    target_blog_ids: [],
  });
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = window.localStorage.getItem('baap_non_secret_settings');
      if (saved) return JSON.parse(saved) as AppSettings;
    } catch {
      // ignore
    }
    return {
      gemini_model: 'gemini-2.5-flash',
      seo_title_min: 45,
      seo_title_max: 65,
      seo_meta_min: 120,
      seo_meta_max: 160,
      default_license_filter: 'commercial_permitted',
      default_timezone: 'UTC',
      image_host_provider: 'none',
      github_owner: '',
      github_repo: '',
      github_branch: 'main',
    };
  });

  // Strictly in-memory session token (never persisted to localStorage)
  const [sessionToken, setSessionToken] = useState('');

  const [confirmState, setConfirmState] = useState<{
    open: boolean;
    title: string;
    description: string;
    confirmLabel?: string;
    danger?: boolean;
    onConfirm: () => void;
  }>({ open: false, title: '', description: '', onConfirm: () => {} });

  const getRepoConfig = useCallback(
    (): GitHubRepoConfig => ({
      owner: settings.github_owner || '',
      repo: settings.github_repo || '',
      branch: settings.github_branch || 'main',
      sessionToken: sessionToken || undefined,
    }),
    [settings.github_owner, settings.github_repo, settings.github_branch, sessionToken]
  );

  const syncData = useCallback(async () => {
    setLoading(true);
    try {
      const cfg = getRepoConfig();
      const snapshot = await loadRepositorySnapshot(cfg.owner && cfg.repo ? cfg : null);
      setArticles(snapshot.articles);
      setBlogs(snapshot.blogs);
      setQueue(snapshot.queue);
      setHistory(snapshot.history);
      setLicenses(snapshot.licenses);
      setSchedule(snapshot.schedule);
      setLogs(snapshot.logs);
      if (snapshot.articles.length > 0 && !selectedArticleId) {
        setSelectedArticleId(snapshot.articles[0].id);
      }
      if (cfg.owner && cfg.repo) {
        const runs = await fetchWorkflowRuns(cfg);
        setWorkflowRuns(runs);
      }
    } catch (err) {
      notify('error', 'Failed to sync repository data', err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [getRepoConfig, notify, selectedArticleId]);

  useEffect(() => {
    void syncData();
  }, [syncData]);

  const handleDispatchGenerate = async (inputs: Record<string, string>) => {
    try {
      await triggerGitHubWorkflow(getRepoConfig(), 'generate-article.yml', inputs);
      notify('success', 'Article generation workflow dispatched', 'Check GitHub Actions or click Sync Data in ~30 seconds.');
    } catch (err) {
      notify('error', 'Could not dispatch generate workflow', err instanceof Error ? err.message : 'Check Settings');
    }
  };

  const handleCreateLocalDraft = (article: Article) => {
    setArticles((prev) => [article, ...prev]);
    setSelectedArticleId(article.id);
    setActive('editor');
    notify('info', 'Working draft opened in Editor', 'Edit HTML, insert licensed images, or dispatch publishing.');
  };

  const handleSaveArticle = (updated: Article) => {
    setArticles((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  const handleInsertImage = (asset: ImageAsset) => {
    const targetId = selectedArticleId || articles[0]?.id;
    if (!targetId) {
      notify('info', 'No active article in Editor', 'Create or select an article first, then insert this image.');
      return;
    }
    const figHtml = `<figure style="margin:24px 0;text-align:center;"><img src="${asset.hosted_url || asset.original_url}" alt="${asset.alt_text || asset.title}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;" /><figcaption style="font-size:0.85em;color:#475569;margin-top:6px;">Image by ${asset.creator_name} via ${asset.source_provider} (<a href="${asset.license_url}" rel="noopener noreferrer" target="_blank">${asset.license_name}</a>)</figcaption></figure>`;
    setArticles((prev) =>
      prev.map((a) =>
        a.id === targetId
          ? {
              ...a,
              html_content: `${a.html_content}\n${figHtml}`,
              images: [...a.images, asset],
              updated_at: new Date().toISOString(),
            }
          : a
      )
    );
    setLicenses((prev) => [asset, ...prev.filter((x) => !(x.id === asset.id && x.source_provider === asset.source_provider))]);
    setActive('editor');
    notify('success', 'Licensed image inserted', `Attribution preserved for ${asset.source_provider} (${asset.license_name}).`);
  };

  const handleTriggerPublish = (article: Article, mode: 'draft' | 'manual') => {
    setConfirmState({
      open: true,
      title: mode === 'draft' ? 'Create Blogger Draft?' : 'Publish Article to Blogger?',
      description: `This dispatches the publish-article.yml GitHub Actions workflow for "${article.title}" in ${mode} mode.`,
      confirmLabel: mode === 'draft' ? 'Create Draft' : 'Publish Now',
      onConfirm: async () => {
        setConfirmState((s) => ({ ...s, open: false }));
        try {
          await triggerGitHubWorkflow(getRepoConfig(), 'publish-article.yml', {
            article_id: article.id,
            target_blog_id: article.blog_id || '',
            publishing_mode: mode,
            scheduled_time: '',
            timezone: settings.default_timezone,
          });
          notify('success', 'Publish workflow dispatched', `Article "${article.title}" queued in GitHub Actions.`);
        } catch (err) {
          notify('error', 'Publish dispatch failed', err instanceof Error ? err.message : 'Check Settings');
        }
      },
    });
  };

  const handleSaveSettings = (updated: AppSettings) => {
    setSettings(updated);
    window.localStorage.setItem('baap_non_secret_settings', JSON.stringify(updated));
    notify('success', 'Settings saved', 'Non-sensitive preferences updated for this browser.');
  };

  return (
    <Layout
      active={active}
      onNavigate={setActive}
      dark={dark}
      onToggleTheme={toggleTheme}
      onRefresh={() => void syncData()}
      loading={loading}
      repoLabel={settings.github_owner && settings.github_repo ? `${settings.github_owner}/${settings.github_repo}` : 'Local / Static Data Mode'}
    >
      {active === 'overview' && (
        <OverviewPage
          articles={articles}
          blogs={blogs}
          queue={queue}
          history={history}
          workflowRuns={workflowRuns}
          onOpenGenerator={() => setActive('generator')}
          onEditArticle={(id) => {
            setSelectedArticleId(id);
            setActive('editor');
          }}
        />
      )}

      {active === 'generator' && (
        <ArticleGeneratorPage
          blogs={blogs}
          defaultTimezone={settings.default_timezone}
          geminiModel={settings.gemini_model}
          onDispatchGenerate={handleDispatchGenerate}
          onCreateLocalDraft={handleCreateLocalDraft}
        />
      )}

      {active === 'editor' && (
        <ArticleEditorPage
          articles={articles}
          selectedArticleId={selectedArticleId}
          blogs={blogs}
          settings={settings}
          onSelectArticle={setSelectedArticleId}
          onSaveArticle={handleSaveArticle}
          onTriggerPublish={handleTriggerPublish}
          onRegenerateArticle={(art) =>
            void handleDispatchGenerate({
              topic: art.main_keyword,
              title: art.title,
              target_blog_id: art.blog_id,
              template: art.template,
              publishing_mode: 'draft',
            })
          }
          onRegenerateParagraph={(art, sel) => {
            if (!sel) {
              notify('info', 'Select a paragraph first', 'Highlight text in Visual mode to dispatch paragraph regeneration.');
              return;
            }
            void handleDispatchGenerate({
              topic: `${art.main_keyword} (rewrite section: ${sel.slice(0, 120)})`,
              title: art.title,
              target_blog_id: art.blog_id,
              template: art.template,
              publishing_mode: 'draft',
            });
          }}
          onOpenImageFinder={() => setActive('images')}
          onNotify={notify}
        />
      )}

      {active === 'images' && (
        <ImageFinderPage
          defaultFilter={settings.default_license_filter}
          savedLicenses={licenses}
          onInsertImage={handleInsertImage}
          onNotify={notify}
        />
      )}

      {active === 'accounts' && (
        <BloggerAccountsPage
          blogs={blogs}
          onAddBlog={(blog) => {
            setBlogs((prev) => [...prev.filter((b) => b.blog_id !== blog.blog_id), blog]);
            notify('success', 'Blog added', `${blog.name} (${blog.blog_id}) added to session list.`);
          }}
          onSyncBlogs={async () => {
            try {
              await triggerGitHubWorkflow(getRepoConfig(), 'validate-project.yml', {});
              notify('success', 'Sync requested', 'Run `python -m backend.main sync-blogs` or refresh after workflow completes.');
            } catch (err) {
              notify('error', 'Sync failed', err instanceof Error ? err.message : 'Configure GitHub repo in Settings');
            }
          }}
        />
      )}

      {active === 'queue' && (
        <PublishingQueuePage
          queue={queue}
          onEditArticle={(id) => {
            setSelectedArticleId(id);
            setActive('editor');
          }}
          onApprove={(qid) => {
            setQueue((prev) => prev.map((q) => (q.queue_id === qid ? { ...q, status: 'Approved' } : q)));
            notify('success', 'Article approved for publishing');
          }}
          onCancel={(qid) => {
            setConfirmState({
              open: true,
              title: 'Cancel Scheduled Article?',
              description: 'This marks the queued item as Cancelled so the scheduler will skip it.',
              confirmLabel: 'Cancel Schedule',
              danger: true,
              onConfirm: () => {
                setQueue((prev) => prev.map((q) => (q.queue_id === qid ? { ...q, status: 'Cancelled' } : q)));
                setConfirmState((s) => ({ ...s, open: false }));
                notify('info', 'Scheduled job cancelled');
              },
            });
          }}
          onReschedule={(qid, isoUtc) => {
            setQueue((prev) =>
              prev.map((q) => (q.queue_id === qid ? { ...q, scheduled_at_utc: isoUtc, status: 'Scheduled' } : q))
            );
            notify('success', 'Publication time updated', `Scheduled for ${isoUtc}`);
          }}
          onRetry={(qid) => {
            setQueue((prev) =>
              prev.map((q) => (q.queue_id === qid ? { ...q, status: 'Scheduled', error_message: '' } : q))
            );
            notify('info', 'Failed item re-queued for retry');
          }}
          onDeleteDraft={(qid) => {
            setConfirmState({
              open: true,
              title: 'Delete Unused Draft?',
              description: 'Remove this draft item from the publishing queue.',
              confirmLabel: 'Delete',
              danger: true,
              onConfirm: () => {
                setQueue((prev) => prev.filter((q) => q.queue_id !== qid));
                setConfirmState((s) => ({ ...s, open: false }));
                notify('info', 'Draft removed from queue');
              },
            });
          }}
          onBulkPublish={async (articleIds, blogIds) => {
            try {
              await triggerGitHubWorkflow(getRepoConfig(), 'manual-bulk-publish.yml', {
                article_ids: articleIds.join(','),
                blog_ids: blogIds.join(','),
                publishing_mode: 'manual',
              });
              notify('success', 'Bulk publish workflow dispatched');
            } catch (err) {
              notify('error', 'Bulk publish failed', err instanceof Error ? err.message : 'Check Settings');
            }
          }}
        />
      )}

      {active === 'history' && <PublishingHistoryPage history={history} blogs={blogs} />}

      {active === 'scheduler' && (
        <AutomationSchedulerPage
          schedule={schedule}
          blogs={blogs}
          onSaveSchedule={(updated) => {
            setSchedule(updated);
            notify('success', 'Schedule configuration updated', 'Commit data/schedule-config.json to persist across GitHub Actions runs.');
          }}
          onRunQueueNow={async () => {
            try {
              await triggerGitHubWorkflow(getRepoConfig(), 'scheduled-publishing.yml', {});
              notify('success', 'Scheduled queue processor dispatched');
            } catch (err) {
              notify('error', 'Failed to run queue processor', err instanceof Error ? err.message : 'Check Settings');
            }
          }}
        />
      )}

      {active === 'settings' && (
        <SettingsPage
          settings={settings}
          sessionToken={sessionToken}
          onSaveSettings={handleSaveSettings}
          onSetSessionToken={setSessionToken}
        />
      )}

      {active === 'logs' && <LogsDiagnosticsPage logs={logs} workflowRuns={workflowRuns} />}

      <ConfirmDialog
        open={confirmState.open}
        title={confirmState.title}
        description={confirmState.description}
        confirmLabel={confirmState.confirmLabel}
        danger={confirmState.danger}
        onConfirm={confirmState.onConfirm}
        onCancel={() => setConfirmState((s) => ({ ...s, open: false }))}
      />

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </Layout>
  );
};
