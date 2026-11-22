"""CLI entrypoint for GitHub Actions workflows and local automation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.ai.article_generator import ArticleGenerator
from backend.ai.gemini_client import GeminiClient
from backend.ai.seo_optimizer import SEOOptimizer
from backend.blogger.blogger_client import BloggerClient
from backend.blogger.oauth import BloggerOAuthManager
from backend.blogger.publisher import BloggerPublisher
from backend.config import AppConfig
from backend.images.image_manager import ImageManager
from backend.models.schemas import (
    ArticleGenerationRequest,
    LicenseFilter,
    PublishingMode,
)
from backend.scheduler.queue import PublishingQueue
from backend.scheduler.scheduler import QueueScheduler
from backend.storage.database import SupabaseAdapter
from backend.storage.repository import RepositoryStorage
from backend.utils.logger import StructuredLogger


def _build_runtime() -> tuple[AppConfig, RepositoryStorage, StructuredLogger]:
    cfg = AppConfig()
    repo = RepositoryStorage(cfg.data_dir)
    logger = StructuredLogger(secrets=cfg.sensitive_values(), log_file=repo.logs_file)
    return cfg, repo, logger


def cmd_generate(args: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    settings = repo.get_settings()
    model = args.model or cfg.gemini_model or settings.get("gemini_model", "gemini-2.5-flash")
    gemini = GeminiClient(cfg.gemini_api_key, model=model)
    generator = ArticleGenerator(gemini, logger=logger)

    secondary = [s.strip() for s in (args.secondary_keywords or "").split(",") if s.strip()]
    req = ArticleGenerationRequest(
        main_keyword=args.keyword,
        article_title=args.title or "",
        secondary_keywords=secondary,
        target_country=args.country,
        target_audience=args.audience,
        language=args.language,
        writing_style=args.style,
        article_length=args.length,
        num_sections=args.sections,
        num_images=args.images,
        blog_id=args.blog_id or cfg.blogger_blog_id,
        template=args.template,
    )
    article = generator.generate(req)

    # Optional automatic copyright-permitted image discovery
    if args.images > 0 and args.fetch_images:
        img_mgr = ImageManager(cfg, repository=repo, logger=logger)
        lic_filter = LicenseFilter(args.license_filter)
        found = []
        for kw in article.image_keywords:
            found.extend(img_mgr.search_permitted_images(kw, license_filter=lic_filter, limit_per_provider=3))
            if len(found) >= args.images:
                break
        if found:
            img_mgr.attach_images_to_article(
                article,
                found[: args.images],
                upload_to_host=(cfg.image_host_provider != "none"),
            )

    # Run SEO analysis
    seo = SEOOptimizer(
        title_min=int(settings.get("seo_title_min", 45)),
        title_max=int(settings.get("seo_title_max", 65)),
        meta_min=int(settings.get("seo_meta_min", 120)),
        meta_max=int(settings.get("seo_meta_max", 160)),
    )
    existing_titles = [a.title for a in repo.list_articles() if a.id != article.id]
    article.seo_analysis = seo.analyze(article, existing_titles=existing_titles).to_dict()
    repo.save_article(article)

    # Enqueue in persistent publishing queue
    queue = PublishingQueue(repo)
    mode = PublishingMode(args.mode)
    target_blog_id = args.blog_id or cfg.blogger_blog_id
    blog = repo.get_blog(target_blog_id) if target_blog_id else None
    q_item = queue.enqueue(
        article,
        target_blog_id=target_blog_id,
        target_blog_name=blog.name if blog else target_blog_id,
        mode=mode,
        scheduled_time=args.scheduled_time or None,
        timezone_name=args.timezone,
    )

    print(json.dumps({"article_id": article.id, "queue_id": q_item.queue_id, "title": article.title}, indent=2))
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    article = repo.get_article(args.article_id)
    if article is None:
        logger.error("cli", f"Article '{args.article_id}' not found.")
        return 1

    oauth = BloggerOAuthManager(
        client_id=cfg.google_client_id,
        client_secret=cfg.google_client_secret,
        refresh_token=cfg.blogger_refresh_token,
    )
    client = BloggerClient(oauth)
    publisher = BloggerPublisher(
        client,
        repo,
        supabase=SupabaseAdapter(cfg),
        logger=logger,
        integration_test_mode=cfg.integration_test_mode,
    )
    target_blog_id = args.blog_id or article.blog_id or cfg.blogger_blog_id
    record = publisher.publish_article(
        article,
        blog_id=target_blog_id,
        mode=PublishingMode(args.mode),
        scheduled_time=args.scheduled_time or None,
        timezone_name=args.timezone,
    )
    print(json.dumps(record.to_dict(), indent=2))
    return 0


def cmd_bulk_publish(args: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    article_ids = [aid.strip() for aid in args.article_ids.split(",") if aid.strip()]
    blog_ids = [bid.strip() for bid in args.blog_ids.split(",") if bid.strip()]
    articles = [a for aid in article_ids if (a := repo.get_article(aid)) is not None]
    if not articles or not blog_ids:
        logger.error("cli", "Bulk publish requires valid article_ids and blog_ids.")
        return 1

    oauth = BloggerOAuthManager(
        client_id=cfg.google_client_id,
        client_secret=cfg.google_client_secret,
        refresh_token=cfg.blogger_refresh_token,
    )
    publisher = BloggerPublisher(
        BloggerClient(oauth),
        repo,
        supabase=SupabaseAdapter(cfg),
        logger=logger,
        integration_test_mode=cfg.integration_test_mode,
    )
    records = publisher.bulk_publish(
        articles,
        blog_ids=blog_ids,
        mode=PublishingMode(args.mode),
        scheduled_time=args.scheduled_time or None,
        timezone_name=args.timezone,
    )
    print(json.dumps([r.to_dict() for r in records], indent=2))
    return 0


def cmd_process_schedule(_: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    oauth = BloggerOAuthManager(
        client_id=cfg.google_client_id,
        client_secret=cfg.google_client_secret,
        refresh_token=cfg.blogger_refresh_token,
    )
    publisher = BloggerPublisher(
        BloggerClient(oauth),
        repo,
        supabase=SupabaseAdapter(cfg),
        logger=logger,
        integration_test_mode=cfg.integration_test_mode,
    )
    scheduler = QueueScheduler(PublishingQueue(repo), publisher, repo, logger=logger)
    result = scheduler.process_due_jobs()
    print(json.dumps(result, indent=2))
    return 0


def cmd_sync_blogs(_: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    oauth = BloggerOAuthManager(
        client_id=cfg.google_client_id,
        client_secret=cfg.google_client_secret,
        refresh_token=cfg.blogger_refresh_token,
    )
    client = BloggerClient(oauth)
    blogs = client.list_blogs()
    repo.save_blogs(blogs)
    logger.info("cli", f"Synced {len(blogs)} Blogger account(s).")
    print(json.dumps([b.to_dict() for b in blogs], indent=2))
    return 0


def cmd_search_images(args: argparse.Namespace) -> int:
    cfg, repo, logger = _build_runtime()
    img_mgr = ImageManager(cfg, repository=repo, logger=logger)
    assets = img_mgr.search_permitted_images(
        args.query,
        license_filter=LicenseFilter(args.license_filter),
        limit_per_provider=args.limit,
    )
    print(json.dumps([a.to_dict() for a in assets], indent=2))
    return 0


def cmd_export_history(args: argparse.Namespace) -> int:
    _, repo, _ = _build_runtime()
    out = repo.export_history_csv() if args.format == "csv" else repo.export_history_json()
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blogger-ai-publisher", description="Blogger AI Auto Publisher CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate an SEO article with Gemini")
    p_gen.add_argument("--keyword", required=True)
    p_gen.add_argument("--title", default="")
    p_gen.add_argument("--secondary-keywords", default="")
    p_gen.add_argument("--country", default="United States")
    p_gen.add_argument("--audience", default="General readers")
    p_gen.add_argument("--language", default="English")
    p_gen.add_argument("--style", default="Informative and practical")
    p_gen.add_argument("--length", default="medium", choices=["short", "medium", "long"])
    p_gen.add_argument("--sections", type=int, default=5)
    p_gen.add_argument("--images", type=int, default=2)
    p_gen.add_argument("--blog-id", default="")
    p_gen.add_argument("--template", default="informational_guide")
    p_gen.add_argument("--mode", default="draft", choices=["manual", "draft", "scheduled", "automatic"])
    p_gen.add_argument("--scheduled-time", default="")
    p_gen.add_argument("--timezone", default="UTC")
    p_gen.add_argument("--model", default="")
    p_gen.add_argument("--fetch-images", action="store_true")
    p_gen.add_argument("--license-filter", default="commercial_permitted")
    p_gen.set_defaults(func=cmd_generate)

    p_pub = sub.add_parser("publish", help="Publish, save draft, or schedule an article")
    p_pub.add_argument("--article-id", required=True)
    p_pub.add_argument("--blog-id", default="")
    p_pub.add_argument("--mode", default="manual", choices=["manual", "draft", "scheduled", "automatic"])
    p_pub.add_argument("--scheduled-time", default="")
    p_pub.add_argument("--timezone", default="UTC")
    p_pub.set_defaults(func=cmd_publish)

    p_bulk = sub.add_parser("bulk-publish", help="Bulk publish articles to multiple blogs")
    p_bulk.add_argument("--article-ids", required=True)
    p_bulk.add_argument("--blog-ids", required=True)
    p_bulk.add_argument("--mode", default="draft", choices=["manual", "draft", "scheduled", "automatic"])
    p_bulk.add_argument("--scheduled-time", default="")
    p_bulk.add_argument("--timezone", default="UTC")
    p_bulk.set_defaults(func=cmd_bulk_publish)

    p_sched = sub.add_parser("process-schedule", help="Process due scheduled queue items")
    p_sched.set_defaults(func=cmd_process_schedule)

    p_sync = sub.add_parser("sync-blogs", help="Sync connected Blogger blogs into data/blogs.json")
    p_sync.set_defaults(func=cmd_sync_blogs)

    p_img = sub.add_parser("search-images", help="Search copyright-permitted images")
    p_img.add_argument("--query", required=True)
    p_img.add_argument("--license-filter", default="commercial_permitted")
    p_img.add_argument("--limit", type=int, default=6)
    p_img.set_defaults(func=cmd_search_images)

    p_exp = sub.add_parser("export-history", help="Export publishing history as CSV or JSON")
    p_exp.add_argument("--format", default="json", choices=["json", "csv"])
    p_exp.add_argument("--output", default="")
    p_exp.set_defaults(func=cmd_export_history)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
