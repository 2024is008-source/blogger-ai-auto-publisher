"""Timezone-aware UTC queue processor designed for GitHub Actions cron drift resilience."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.blogger.publisher import BloggerPublisher
from backend.models.schemas import ArticleStatus, PublishingMode, QueueItem, utc_now_iso
from backend.scheduler.queue import PublishingQueue
from backend.storage.repository import RepositoryStorage
from backend.utils.logger import StructuredLogger


class QueueScheduler:
    """Processes due scheduled queue items while enforcing daily caps and retry recovery."""

    def __init__(
        self,
        queue: PublishingQueue,
        publisher: BloggerPublisher,
        repository: RepositoryStorage,
        *,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.queue = queue
        self.publisher = publisher
        self.repository = repository
        self.logger = logger or StructuredLogger()

    def process_due_jobs(self, *, now_utc: datetime | None = None) -> dict[str, list[str]]:
        """Check all due Scheduled jobs (and retryable Approved jobs) and publish up to max_daily_posts."""
        current = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
        schedule_cfg = self.repository.get_schedule_config()
        published_today = self._count_published_today(current)
        remaining_quota = max(0, schedule_cfg.max_daily_posts - published_today)

        summary: dict[str, list[str]] = {"published": [], "failed": [], "skipped": []}
        if remaining_quota <= 0:
            self.logger.info(
                "scheduler",
                "Daily publishing cap reached; skipping due jobs until next UTC day.",
                published_today=published_today,
                max_daily_posts=schedule_cfg.max_daily_posts,
            )
            return summary

        due_items = self._find_due_items(current)
        for item in due_items:
            if len(summary["published"]) >= remaining_quota:
                summary["skipped"].append(item.queue_id)
                continue

            article = self.repository.get_article(item.article_id)
            if article is None:
                self.queue.update_status(
                    item.queue_id,
                    ArticleStatus.FAILED,
                    error_message=f"Referenced article '{item.article_id}' not found in repository.",
                    increment_retry=True,
                )
                summary["failed"].append(item.queue_id)
                continue

            self.queue.update_status(item.queue_id, ArticleStatus.PUBLISHING)
            try:
                mode = (
                    PublishingMode.DRAFT
                    if item.publishing_mode == PublishingMode.DRAFT.value
                    else PublishingMode.AUTOMATIC
                )
                record = self.publisher.publish_article(
                    article,
                    blog_id=item.target_blog_id,
                    mode=mode,
                )
                final_status = (
                    ArticleStatus.DRAFT if record.status == ArticleStatus.DRAFT.value else ArticleStatus.PUBLISHED
                )
                self.queue.update_status(
                    item.queue_id,
                    final_status,
                    blogger_post_id=record.blogger_post_id,
                    post_url=record.article_url,
                    published_at_utc=utc_now_iso(),
                )
                summary["published"].append(item.queue_id)
            except Exception as exc:
                self.queue.update_status(
                    item.queue_id,
                    ArticleStatus.FAILED,
                    error_message=str(exc),
                    increment_retry=True,
                )
                summary["failed"].append(item.queue_id)

        return summary

    def _find_due_items(self, now_utc: datetime) -> list[QueueItem]:
        due: list[QueueItem] = []
        for item in self.queue.list_items():
            if item.status != ArticleStatus.SCHEDULED.value:
                continue
            if not item.scheduled_at_utc:
                continue
            try:
                sched_dt = datetime.fromisoformat(item.scheduled_at_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                continue
            if sched_dt <= now_utc:
                due.append(item)
        due.sort(key=lambda i: i.scheduled_at_utc or "")
        return due

    def _count_published_today(self, now_utc: datetime) -> int:
        today_prefix = now_utc.strftime("%Y-%m-%d")
        return sum(
            1
            for rec in self.repository.list_history()
            if rec.status == ArticleStatus.PUBLISHED.value and rec.timestamp_utc.startswith(today_prefix)
        )
