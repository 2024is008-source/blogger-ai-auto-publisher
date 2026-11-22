"""Persistent publishing queue manager supporting all 9 article lifecycle statuses."""

from __future__ import annotations

from backend.blogger.publisher import to_utc_rfc3339
from backend.models.schemas import Article, ArticleStatus, PublishingMode, QueueItem
from backend.storage.repository import RepositoryStorage


class PublishingQueue:
    """Manages persistent queue items stored in data/queue.json."""

    def __init__(self, repository: RepositoryStorage) -> None:
        self.repository = repository

    def list_items(self, *, status: str | None = None, blog_id: str | None = None) -> list[QueueItem]:
        items = self.repository.list_queue()
        if status:
            items = [i for i in items if i.status == status]
        if blog_id:
            items = [i for i in items if i.target_blog_id == blog_id]
        return items

    def enqueue(
        self,
        article: Article,
        *,
        target_blog_id: str,
        target_blog_name: str = "",
        mode: PublishingMode = PublishingMode.MANUAL,
        scheduled_time: str | None = None,
        timezone_name: str = "UTC",
        initial_status: ArticleStatus | None = None,
    ) -> QueueItem:
        items = self.repository.list_queue()
        scheduled_utc = to_utc_rfc3339(scheduled_time, timezone_name) if scheduled_time else None

        status = initial_status
        if status is None:
            if scheduled_utc:
                status = ArticleStatus.SCHEDULED
            elif mode == PublishingMode.DRAFT:
                status = ArticleStatus.DRAFT
            else:
                status = ArticleStatus.GENERATED

        item = QueueItem(
            article_id=article.id,
            title=article.title,
            target_blog_id=target_blog_id,
            target_blog_name=target_blog_name or target_blog_id,
            article_content_ref=f"data/articles/{article.id}.json",
            publishing_mode=mode.value,
            status=status.value,
            scheduled_at_utc=scheduled_utc,
            timezone_name=timezone_name,
        )
        items.append(item)
        self.repository.save_queue(items)
        return item

    def get_item(self, queue_id: str) -> QueueItem | None:
        for item in self.repository.list_queue():
            if item.queue_id == queue_id:
                return item
        return None

    def update_status(
        self,
        queue_id: str,
        status: ArticleStatus,
        *,
        error_message: str = "",
        blogger_post_id: str | None = None,
        post_url: str | None = None,
        published_at_utc: str | None = None,
        increment_retry: bool = False,
    ) -> QueueItem:
        items = self.repository.list_queue()
        for item in items:
            if item.queue_id == queue_id:
                item.status = status.value
                item.error_message = error_message
                if blogger_post_id is not None:
                    item.blogger_post_id = blogger_post_id
                if post_url is not None:
                    item.post_url = post_url
                if published_at_utc is not None:
                    item.published_at_utc = published_at_utc
                if increment_retry:
                    item.retry_count += 1
                self.repository.save_queue(items)
                return item
        raise KeyError(f"Queue item '{queue_id}' not found.")

    def approve(self, queue_id: str) -> QueueItem:
        return self.update_status(queue_id, ArticleStatus.APPROVED)

    def cancel(self, queue_id: str) -> QueueItem:
        return self.update_status(queue_id, ArticleStatus.CANCELLED)

    def reschedule(self, queue_id: str, new_time: str, timezone_name: str = "UTC") -> QueueItem:
        utc_ts = to_utc_rfc3339(new_time, timezone_name)
        items = self.repository.list_queue()
        for item in items:
            if item.queue_id == queue_id:
                item.scheduled_at_utc = utc_ts
                item.timezone_name = timezone_name
                item.status = ArticleStatus.SCHEDULED.value
                item.error_message = ""
                self.repository.save_queue(items)
                return item
        raise KeyError(f"Queue item '{queue_id}' not found.")

    def mark_for_retry(self, queue_id: str) -> QueueItem:
        items = self.repository.list_queue()
        for item in items:
            if item.queue_id == queue_id:
                if item.retry_count >= item.max_retries:
                    raise RuntimeError(f"Queue item '{queue_id}' reached max retries ({item.max_retries}).")
                item.status = ArticleStatus.SCHEDULED.value if item.scheduled_at_utc else ArticleStatus.APPROVED.value
                item.error_message = ""
                self.repository.save_queue(items)
                return item
        raise KeyError(f"Queue item '{queue_id}' not found.")

    def delete_unused_draft(self, queue_id: str) -> bool:
        items = self.repository.list_queue()
        kept: list[QueueItem] = []
        removed = False
        for item in items:
            if item.queue_id == queue_id and item.status in {
                ArticleStatus.DRAFT.value,
                ArticleStatus.GENERATED.value,
                ArticleStatus.CANCELLED.value,
            }:
                removed = True
                continue
            kept.append(item)
        if removed:
            self.repository.save_queue(kept)
        return removed
