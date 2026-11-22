"""Complete Blogger publishing engine with duplicate prevention, timezone-aware scheduling, and status verification."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.blogger.blogger_client import BloggerClient
from backend.models.schemas import (
    Article,
    ArticleStatus,
    PublishingHistoryRecord,
    PublishingMode,
    utc_now_iso,
)
from backend.storage.database import SupabaseAdapter
from backend.storage.repository import RepositoryStorage
from backend.utils.errors import BloggerAPIError, DuplicateArticleError, InvalidScheduleError
from backend.utils.logger import StructuredLogger


def to_utc_rfc3339(local_iso_or_utc: str, tz_name: str = "UTC") -> str:
    """Convert a local or timezone-aware ISO datetime string into UTC RFC 3339 format."""
    if not local_iso_or_utc or not local_iso_or_utc.strip():
        raise InvalidScheduleError("Scheduled publication timestamp is required.")
    raw = local_iso_or_utc.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidScheduleError(f"Invalid ISO-8601 timestamp '{local_iso_or_utc}': {exc}") from exc

    if dt.tzinfo is None:
        try:
            tz = ZoneInfo(tz_name or "UTC")
        except ZoneInfoNotFoundError as exc:
            raise InvalidScheduleError(f"Unknown timezone '{tz_name}'.") from exc
        dt = dt.replace(tzinfo=tz)

    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class BloggerPublisher:
    """Handles immediate, draft, scheduled, and bulk publishing with strict verification."""

    def __init__(
        self,
        client: BloggerClient,
        repository: RepositoryStorage,
        *,
        supabase: SupabaseAdapter | None = None,
        logger: StructuredLogger | None = None,
        integration_test_mode: bool = False,
    ) -> None:
        self.client = client
        self.repository = repository
        self.supabase = supabase
        self.logger = logger or StructuredLogger()
        self.integration_test_mode = integration_test_mode

    def is_duplicate(self, article_id: str, blog_id: str) -> bool:
        """Prevent accidental duplicate publication of the same article to the same blog."""
        for rec in self.repository.list_history():
            if (
                rec.article_id == article_id
                and rec.blog_id == blog_id
                and rec.status in {ArticleStatus.PUBLISHED.value, ArticleStatus.SCHEDULED.value}
                and rec.blogger_post_id
            ):
                return True
        return False

    def publish_article(
        self,
        article: Article,
        *,
        blog_id: str,
        mode: PublishingMode = PublishingMode.MANUAL,
        scheduled_time: str | None = None,
        timezone_name: str = "UTC",
        allow_duplicate: bool = False,
    ) -> PublishingHistoryRecord:
        """Publish, save as draft, or schedule an article on a specific Blogger website."""
        if not blog_id:
            raise ValueError("A target blog_id is required.")
        if not allow_duplicate and self.is_duplicate(article.id, blog_id):
            raise DuplicateArticleError(
                f"Article '{article.id}' has already been published or scheduled on blog '{blog_id}'."
            )

        blog = self.repository.get_blog(blog_id)
        blog_name = blog.name if blog else f"Blog {blog_id}"
        labels = list(dict.fromkeys((article.labels or []) + (blog.default_labels if blog else [])))
        image_sources = sorted({img.source_provider for img in article.images if img.source_provider})

        is_draft = mode == PublishingMode.DRAFT
        scheduled_utc: str | None = None
        if mode == PublishingMode.SCHEDULED:
            scheduled_utc = to_utc_rfc3339(scheduled_time or "", timezone_name)

        if self.integration_test_mode:
            self.logger.info(
                "publisher",
                "Integration test mode active: simulating Blogger publish without calling live API.",
                article_id=article.id,
                blog_id=blog_id,
                mode=mode.value,
            )
            simulated_status = (
                ArticleStatus.DRAFT.value
                if is_draft
                else (ArticleStatus.SCHEDULED.value if mode == PublishingMode.SCHEDULED else ArticleStatus.PUBLISHED.value)
            )
            record = PublishingHistoryRecord(
                article_id=article.id,
                article_title=article.title,
                blog_id=blog_id,
                blog_name=blog_name,
                status=simulated_status,
                timestamp_utc=utc_now_iso(),
                blogger_post_id=f"sim_{article.id}_{blog_id}",
                article_url=f"https://example.blogspot.com/simulated/{article.slug}",
                image_sources=image_sources,
                publishing_mode=mode.value,
                main_keyword=article.main_keyword,
            )
            self._persist_record(article, record)
            return record

        try:
            response = self.client.create_post(
                blog_id,
                title=article.title,
                content_html=article.html_content,
                labels=labels,
                is_draft=is_draft,
                scheduled_published_rfc3339=scheduled_utc,
            )
            returned_status = str(response.get("status") or "").upper()
            post_id = str(response.get("id") or "").strip()
            post_url = str(response.get("url") or "").strip()

            if not post_id:
                raise BloggerAPIError("Blogger API did not return a post ID; publication cannot be confirmed.")

            # Verify actual returned status from Blogger API v3
            if is_draft:
                final_status = ArticleStatus.DRAFT.value
            elif mode == PublishingMode.SCHEDULED:
                if returned_status not in {"SCHEDULED", "LIVE"}:
                    raise BloggerAPIError(
                        f"Blogger returned unexpected status '{returned_status}' for scheduled post {post_id}."
                    )
                final_status = (
                    ArticleStatus.SCHEDULED.value if returned_status == "SCHEDULED" else ArticleStatus.PUBLISHED.value
                )
            else:
                if returned_status != "LIVE":
                    raise BloggerAPIError(
                        f"Blogger did not confirm LIVE publication (returned status: '{returned_status or 'UNKNOWN'}')."
                    )
                final_status = ArticleStatus.PUBLISHED.value

            record = PublishingHistoryRecord(
                article_id=article.id,
                article_title=article.title,
                blog_id=blog_id,
                blog_name=blog_name,
                status=final_status,
                timestamp_utc=utc_now_iso(),
                blogger_post_id=post_id,
                article_url=post_url,
                image_sources=image_sources,
                publishing_mode=mode.value,
                main_keyword=article.main_keyword,
            )
            self._persist_record(article, record)
            self.logger.info(
                "publisher",
                f"Post verified with status {final_status}",
                article_id=article.id,
                blog_id=blog_id,
                blogger_post_id=post_id,
            )
            return record

        except Exception as exc:
            failed_record = PublishingHistoryRecord(
                article_id=article.id,
                article_title=article.title,
                blog_id=blog_id,
                blog_name=blog_name,
                status=ArticleStatus.FAILED.value,
                timestamp_utc=utc_now_iso(),
                image_sources=image_sources,
                publishing_mode=mode.value,
                main_keyword=article.main_keyword,
                error_details=str(exc),
            )
            self.repository.append_history(failed_record)
            self.logger.error(
                "publisher",
                "Publishing failed",
                article_id=article.id,
                blog_id=blog_id,
                error=str(exc),
            )
            raise

    def bulk_publish(
        self,
        articles: list[Article],
        *,
        blog_ids: list[str],
        mode: PublishingMode = PublishingMode.MANUAL,
        scheduled_time: str | None = None,
        timezone_name: str = "UTC",
    ) -> list[PublishingHistoryRecord]:
        """Publish multiple articles across one or more target blogs, capturing per-item failures without aborting."""
        results: list[PublishingHistoryRecord] = []
        for article in articles:
            for blog_id in blog_ids:
                try:
                    rec = self.publish_article(
                        article,
                        blog_id=blog_id,
                        mode=mode,
                        scheduled_time=scheduled_time,
                        timezone_name=timezone_name,
                    )
                    results.append(rec)
                except Exception as exc:
                    results.append(
                        PublishingHistoryRecord(
                            article_id=article.id,
                            article_title=article.title,
                            blog_id=blog_id,
                            blog_name=blog_id,
                            status=ArticleStatus.FAILED.value,
                            publishing_mode=mode.value,
                            main_keyword=article.main_keyword,
                            error_details=str(exc),
                        )
                    )
        return results

    def _persist_record(self, article: Article, record: PublishingHistoryRecord) -> None:
        article.status = record.status
        self.repository.save_article(article)
        self.repository.append_history(record)
        if self.supabase and self.supabase.enabled:
            try:
                self.supabase.upsert("publishing_history", record.to_dict())
            except Exception as exc:
                self.logger.warning("publisher", "Supabase sync failed; repository JSON remains authoritative.", error=str(exc))
