export type NavSection =
  | 'overview'
  | 'generator'
  | 'editor'
  | 'images'
  | 'accounts'
  | 'queue'
  | 'history'
  | 'scheduler'
  | 'settings'
  | 'logs';

export type ArticleStatus =
  | 'Generated'
  | 'Editing'
  | 'Approved'
  | 'Draft'
  | 'Scheduled'
  | 'Publishing'
  | 'Published'
  | 'Failed'
  | 'Cancelled';

export type PublishingMode = 'manual' | 'draft' | 'scheduled' | 'automatic';

export type LicenseFilter =
  | 'cc0_public_domain'
  | 'commercial_permitted'
  | 'cc_with_attribution'
  | 'all_supported';

export interface ImageAsset {
  id: string;
  title: string;
  original_url: string;
  preview_url: string;
  creator_name: string;
  source_provider: string;
  license_name: string;
  license_url: string;
  attribution_required: boolean;
  attribution_text: string;
  retrieval_date: string;
  commercial_use_permitted: boolean | null;
  hosted_url: string;
  alt_text: string;
  width?: number | null;
  height?: number | null;
}

export interface SEOCheck {
  check: string;
  status: 'pass' | 'warning' | 'fail';
  message: string;
  recommendation: string;
}

export interface SEOAnalysisResult {
  score: number;
  checks: SEOCheck[];
  word_count: number;
  readability_grade: number;
  heading_counts: Record<string, number>;
  internal_link_count: number;
  external_link_count: number;
  disclaimer: string;
}

export interface Article {
  id: string;
  title: string;
  suggested_titles: string[];
  slug: string;
  meta_description: string;
  main_keyword: string;
  secondary_keywords: string[];
  labels: string[];
  outline: string[];
  html_content: string;
  image_keywords: string[];
  image_alt_texts: string[];
  images: ImageAsset[];
  template: string;
  language: string;
  target_country: string;
  target_audience: string;
  blog_id: string;
  status: ArticleStatus;
  seo_analysis: SEOAnalysisResult | null;
  created_at: string;
  updated_at: string;
}

export interface BlogAccount {
  blog_id: string;
  name: string;
  url: string;
  description: string;
  locale: string;
  default_labels: string[];
  default_timezone: string;
  max_daily_posts: number;
  active: boolean;
  last_synced_at: string;
}

export interface QueueItem {
  queue_id: string;
  article_id: string;
  title: string;
  target_blog_id: string;
  target_blog_name: string;
  article_content_ref: string;
  publishing_mode: PublishingMode;
  status: ArticleStatus;
  created_at: string;
  scheduled_at_utc: string | null;
  timezone_name: string;
  published_at_utc: string | null;
  blogger_post_id: string | null;
  post_url: string | null;
  error_message: string;
  retry_count: number;
  max_retries: number;
}

export interface PublishingHistoryRecord {
  record_id: string;
  article_id: string;
  article_title: string;
  blog_id: string;
  blog_name: string;
  status: ArticleStatus;
  timestamp_utc: string;
  blogger_post_id: string;
  article_url: string;
  image_sources: string[];
  publishing_mode: PublishingMode;
  main_keyword: string;
  error_details: string;
}

export interface ScheduleConfig {
  enabled: boolean;
  frequency: 'daily' | 'weekly' | 'custom';
  days_of_week: string[];
  preferred_time_local: string;
  timezone_name: string;
  max_daily_posts: number;
  target_blog_ids: string[];
}

export interface AppSettings {
  gemini_model: string;
  seo_title_min: number;
  seo_title_max: number;
  seo_meta_min: number;
  seo_meta_max: number;
  default_license_filter: LicenseFilter;
  default_timezone: string;
  image_host_provider: 'none' | 'cloudinary' | 'github';
  github_owner?: string;
  github_repo?: string;
  github_branch?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  component: string;
  message: string;
  context: Record<string, string>;
}

export interface WorkflowRunSummary {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  created_at: string;
  html_url: string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  detail?: string;
}
