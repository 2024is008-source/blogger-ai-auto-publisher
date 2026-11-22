<<<<<<< HEAD
# Blogger AI Auto Publisher

A serverless, zero-cost, production-ready platform for generating SEO-structured blog articles with Google Gemini, discovering copyright-verified images, managing multiple Google Blogger websites, and automating scheduled publishing through GitHub Pages and GitHub Actions.

---

## Architecture Overview

```text
+-----------------------------------------------------------------------+
|                       GitHub Pages (Frontend)                         |
|  React + TypeScript + Vite + Tailwind CSS + Lucide Icons              |
|  - 10-Section SaaS Dashboard (Light/Dark, Responsive)                 |
|  - Rich Text / HTML / Preview Editor + Live 12-Check SEO Analyzer     |
|  - Openverse & Wikimedia Live Image Finder (Asset-Level Licensing)    |
|  - Reads non-sensitive data/ JSON + GitHub Actions Workflow Status    |
+-------------------------------+---------------------------------------+
                                | workflow_dispatch / cron
                                v
+-----------------------------------------------------------------------+
|                   GitHub Actions (Serverless Backend)                 |
|  Python 3.12+ Modular Automation Engine (Secrets in GitHub Secrets)   |
|  - generate-article.yml       -> Gemini API + Image Discovery + SEO   |
|  - publish-article.yml        -> Blogger API v3 (Live/Draft/Schedule) |
|  - scheduled-publishing.yml   -> UTC Cron Queue Processor (30m)       |
|  - manual-bulk-publish.yml    -> Multi-Article / Multi-Blog Publish   |
|  - validate-project.yml       -> Unit/Integration Tests + Vite Build  |
|  - deploy-pages.yml           -> Builds & Deploys Dashboard + data/   |
+---------------+-----------------------+--------------------+----------+
                |                       |                    |
                v                       v                    v
      Google Gemini API      Image Providers & Host    Google Blogger API v3
   (Configurable Model)      Openverse, Wikimedia,     OAuth 2.0 Refresh Token
                             Pexels, Pixabay +         Multi-Blog Publishing
                             Cloudinary / GitHub Host  Status Verification
                |
                v
+-----------------------------------------------------------------------+
|                         Persistent Storage                            |
|  - GitHub Repository `data/` (articles, queue, history, licenses)     |
|  - GitHub Actions Artifacts (per-run JSON reports)                    |
|  - Optional Supabase PostgREST (multi-user / centralized persistence) |
+-----------------------------------------------------------------------+
```

---

## Key Features

- **10-Section SaaS Dashboard**: Overview, Article Generator, Article Editor, Image Finder, Blogger Accounts, Publishing Queue, Publishing History, Automation Scheduler, Settings, and Logs & Diagnostics.
- **10-Step Gemini Article Workflow**: Topic intake, SEO title suggestions, outline generation, Blogger-compatible HTML body, meta description, slug, Blogger labels, image search keywords, accessible alt text, and HTML structure validation across 7 configurable templates.
- **Rich Text + HTML Source + Live Preview Editor**: Preserves HTML cleanly across modes, supports H2/H3 headings, lists, links, tables, image insertion/resizing, paragraph/full regeneration, copy HTML, and live 12-check SEO diagnostics (with explicit disclaimer that on-page scores do not guarantee rankings).
- **Asset-Level Copyright-Permitted Image Discovery**: Modular provider architecture integrating Openverse, Wikimedia Commons, Pexels, and Pixabay. Every image is validated at the individual asset level against your selected license filter (`CC0 / Public Domain`, `Commercial-use permitted`, `Creative Commons with attribution`, or `All supported`), retaining creator, license URL, attribution text, and retrieval date.
- **Blogger-Compatible Image Hosting**: Because Blogger API v3 does not expose a general-purpose image upload endpoint, the uploader supports authorized hosting via Cloudinary or a public GitHub asset repository, verifies public URL accessibility, and explicitly reports missing configuration rather than faking uploads.
- **Official Google Blogger API v3 & Multi-Blog Support**: Secure OAuth 2.0 refresh token management, blog synchronization, live/draft/scheduled/bulk publishing, strict Blogger post-status verification, and duplicate-publishing prevention per `(article_id, blog_id)`.
- **Timezone-Aware UTC Queue & Cron Resilience**: Stores all scheduled times in UTC; the GitHub Actions queue processor runs every 30 minutes and publishes due jobs (`scheduled_at_utc <= now_utc`) up to your configured daily cap.
- **Zero Secrets in Frontend or Repository**: All API keys and OAuth tokens remain strictly inside GitHub Secrets; structured logs automatically redact sensitive tokens.

---

## Technology Stack

- **Frontend**: React 18, TypeScript 5, Vite 6, Tailwind CSS 3, Lucide React
- **Backend**: Python 3.12+, BeautifulSoup4, standard-library resilient HTTP client with exponential backoff
- **Automation & Hosting**: GitHub Actions, GitHub Pages
- **APIs**: Google Gemini API, Google Blogger API v3, Openverse API, Wikimedia Commons API, Pexels API, Pixabay API, optional Supabase REST API

---

## Step-by-Step Setup Guide

### 1. Create Your GitHub Repository
1. Create a new GitHub repository named `blogger-ai-auto-publisher`.
2. Push this codebase to the `main` branch.

### 2. Enable GitHub Pages
1. Open your repository on GitHub and go to **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Push to `main` (or manually run **Deploy Dashboard to GitHub Pages** under the **Actions** tab).
4. Once complete, your dashboard is live at `https://<your-username>.github.io/blogger-ai-auto-publisher/`.

### 3. Obtain a Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/apikey) and create an API key.
2. Save this key for Step 6 (`GEMINI_API_KEY`).
3. You can configure any supported Gemini model via the repository variable `GEMINI_MODEL` (defaults to `gemini-2.5-flash`).

### 4. Set Up Google Cloud Project & Activate Blogger API v3
1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g., `Blogger AI Auto Publisher`).
2. Navigate to **APIs & Services → Library**, search for **Blogger API v3**, and click **Enable**.
3. Navigate to **APIs & Services → OAuth consent screen**:
   - Choose **External** (or Internal if using Google Workspace).
   - Add your email as a **Test User** while in Testing mode.
   - Add the scope: `https://www.googleapis.com/auth/blogger`.
4. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app** (or Web application with authorized redirect URI `http://127.0.0.1:8765/oauth2callback`).
   - Copy your `Client ID` (`GOOGLE_CLIENT_ID`) and `Client Secret` (`GOOGLE_CLIENT_SECRET`).

### 5. Generate Your Secure Blogger Refresh Token (One-Time Local Step)
Never commit credentials or tokens into Git. Run the included local helper on your workstation:

```bash
python3 scripts/setup_blogger_oauth.py
```

Follow the browser prompt to authorize your Blogger account. Copy the printed refresh token for `BLOGGER_REFRESH_TOKEN`.

### 6. Configure GitHub Secrets & Variables
Go to your repository's **Settings → Secrets and variables → Actions**.

Add these **Repository Secrets**:

| Secret Name | Required | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes | Google Gemini API key for article generation |
| `GOOGLE_CLIENT_ID` | Yes | Google Cloud OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google Cloud OAuth 2.0 Client Secret |
| `BLOGGER_REFRESH_TOKEN` | Yes | Long-lived OAuth 2.0 refresh token (`blogger` scope) |
| `BLOGGER_BLOG_ID` | Yes | Default numeric Blogger Blog ID |
| `PEXELS_API_KEY` | Optional | Pexels API key for stock photo search |
| `PIXABAY_API_KEY` | Optional | Pixabay API key for stock photo search |
| `CLOUDINARY_CLOUD_NAME` | Optional | Required if `IMAGE_HOST_PROVIDER=cloudinary` |
| `CLOUDINARY_UPLOAD_PRESET` | Optional | Unsigned upload preset for Cloudinary |
| `SUPABASE_URL` | Optional | Supabase project URL for centralized persistence |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase service role key (never exposed to frontend) |

Add these optional **Repository Variables** (non-sensitive):

| Variable Name | Default | Purpose |
| --- | --- | --- |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Configurable Gemini model ID |
| `OPENVERSE_ENABLED` | `true` | Enable Openverse CC/PD image discovery |
| `IMAGE_HOST_PROVIDER` | `none` | `none`, `cloudinary`, or `github` |
| `GITHUB_IMAGE_REPO` | *(empty)* | `owner/repo` if using `github` image hosting |

### 7. Activate GitHub Actions Workflows
1. Go to **Settings → Actions → General → Workflow permissions** and enable **Read and write permissions** so workflows can persist updates to `data/`.
2. Open the **Actions** tab and verify all workflows are enabled:
   - `Generate SEO Article` (`generate-article.yml`)
   - `Publish Article to Blogger` (`publish-article.yml`)
   - `Scheduled Queue Publishing` (`scheduled-publishing.yml`)
   - `Manual Bulk Publish` (`manual-bulk-publish.yml`)
   - `Validate Project & Security Checks` (`validate-project.yml`)
   - `Deploy Dashboard to GitHub Pages` (`deploy-pages.yml`)

### 8. First Article Generation, Test Draft, and Real Publication
1. **Generate**: Open **Actions → Generate SEO Article → Run workflow**, enter a topic (e.g., `indoor herb gardening`), keep `publishing_mode` set to `draft`, and run. The workflow generates the article, attaches copyright-permitted images, runs SEO analysis, commits `data/articles/<id>.json`, and adds it to `data/queue.json`.
2. **Review & Edit**: Open your GitHub Pages dashboard, configure your GitHub owner/repo in **Settings**, click **Sync Data**, and open the article in **Article Editor**.
3. **First Test Draft**: Run **Publish Article to Blogger** with `publishing_mode: draft` and your `article_id`. Confirm the draft appears in your Blogger admin dashboard.
4. **First Real Publication**: Run **Publish Article to Blogger** with `publishing_mode: manual` (or click **Publish** in the dashboard with an ephemeral session PAT). Blogger API v3 confirms `LIVE` status before recording it in `data/publishing-history/history.json`.

### 9. Scheduling Configuration
1. Edit `data/schedule-config.json` (or configure it in **Automation Scheduler**): set `enabled: true`, `timezone_name`, `preferred_time_local`, `days_of_week`, and `max_daily_posts`.
2. Enqueue articles with `publishing_mode: scheduled` and a target timestamp.
3. `.github/workflows/scheduled-publishing.yml` runs every 30 minutes (`*/30 * * * *`) and publishes every due item (`scheduled_at_utc <= now_utc`) up to `max_daily_posts`.

---

## Local Development & Testing

```bash
# Run Python unit and integration tests (uses mocked APIs; never publishes to real blogs)
INTEGRATION_TEST_MODE=true python3 -m unittest discover -s tests -v

# Run frontend locally
cd frontend
npm install
npm run dev
```

---

## Troubleshooting

- **Blogger 401 / `invalid_grant` error**: Your OAuth refresh token expired or was revoked (Google Testing apps expire refresh tokens after 7 days unless published). Re-run `python3 scripts/setup_blogger_oauth.py` and update `BLOGGER_REFRESH_TOKEN` in GitHub Secrets.
- **`IMAGE_UPLOAD_NOT_CONFIGURED` error**: Blogger API v3 has no general media upload endpoint. Configure `IMAGE_HOST_PROVIDER=cloudinary` (with `CLOUDINARY_CLOUD_NAME` and `CLOUDINARY_UPLOAD_PRESET`) or `IMAGE_HOST_PROVIDER=github` (with `GITHUB_IMAGE_REPO`).
- **GitHub Actions `git push` rejected**: Confirm **Settings → Actions → General → Workflow permissions** is set to **Read and write permissions**.
- **Scheduled posts delayed by a few minutes**: GitHub Actions cron triggers can queue under load; this is expected. The queue processor handles drift automatically by evaluating `scheduled_at_utc <= now_utc`.
=======
# blogger-ai-auto-publisher
>>>>>>> d96a88fee59f9bd740c013d431fc8b849ccced61
