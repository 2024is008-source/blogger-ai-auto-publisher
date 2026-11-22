"""Tests for persistent publishing queue, timezone-aware scheduler, daily cap, and error recovery."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.blogger.blogger_client import BloggerClient
from backend.blogger.oauth import BloggerOAuthManager
from backend.blogger.publisher import BloggerPublisher
from backend.models.schemas import Article, ArticleStatus, PublishingMode, ScheduleConfig
from backend.scheduler.queue import PublishingQueue
from backend.scheduler.scheduler import QueueScheduler
from backend.storage.repository import RepositoryStorage


class TestQueueAndScheduler(unittest.TestCase):
    def test_queue_persistence_and_lifecycle_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositoryStorage(Path(tmp))
            queue = PublishingQueue(repo)
            art = Article(id="art_q1", title="Queued Post", html_content="<p>Body</p>")
            repo.save_article(art)

            item = queue.enqueue(
                art,
                target_blog_id="blog_1",
                target_blog_name="Main Blog",
                mode=PublishingMode.SCHEDULED,
                scheduled_time="2026-11-25T10:00:00",
                timezone_name="America/New_York",
            )
            self.assertEqual(item.status, ArticleStatus.SCHEDULED.value)
            # America/New_York in November is UTC-5 -> 15:00Z
            self.assertEqual(item.scheduled_at_utc, "2026-11-25T15:00:00Z")

            # Re-instantiate queue to prove persistence across runs
            queue2 = PublishingQueue(RepositoryStorage(Path(tmp)))
            reloaded = queue2.get_item(item.queue_id)
            self.assertIsNotNone(reloaded)
            assert reloaded is not None
            self.assertEqual(reloaded.title, "Queued Post")

            queue2.approve(item.queue_id)
            self.assertEqual(queue2.get_item(item.queue_id).status, ArticleStatus.APPROVED.value)

            queue2.cancel(item.queue_id)
            self.assertEqual(queue2.get_item(item.queue_id).status, ArticleStatus.CANCELLED.value)
            self.assertTrue(queue2.delete_unused_draft(item.queue_id))
            self.assertIsNone(queue2.get_item(item.queue_id))

    def test_scheduler_processes_due_jobs_enforces_daily_cap_and_recovers_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositoryStorage(Path(tmp))
            repo.save_schedule_config(ScheduleConfig(enabled=True, max_daily_posts=1))
            queue = PublishingQueue(repo)

            art1 = Article(id="art_due_1", title="Due Post 1", html_content="<p>Body 1</p>")
            art2 = Article(id="art_due_2", title="Due Post 2", html_content="<p>Body 2</p>")
            art_future = Article(id="art_future", title="Future Post", html_content="<p>Body 3</p>")
            repo.save_article(art1)
            repo.save_article(art2)
            repo.save_article(art_future)

            q1 = queue.enqueue(art1, target_blog_id="b1", mode=PublishingMode.SCHEDULED, scheduled_time="2026-11-22T08:00:00Z")
            q2 = queue.enqueue(art2, target_blog_id="b1", mode=PublishingMode.SCHEDULED, scheduled_time="2026-11-22T08:30:00Z")
            q_fut = queue.enqueue(art_future, target_blog_id="b1", mode=PublishingMode.SCHEDULED, scheduled_time="2026-11-23T08:00:00Z")

            oauth = BloggerOAuthManager(client_id="c", client_secret="s", refresh_token="r")
            publisher = BloggerPublisher(BloggerClient(oauth), repo, integration_test_mode=True)
            scheduler = QueueScheduler(queue, publisher, repo)

            now = datetime(2026, 11, 22, 9, 0, tzinfo=timezone.utc)
            result = scheduler.process_due_jobs(now_utc=now)

            self.assertEqual(result["published"], [q1.queue_id])
            self.assertEqual(result["skipped"], [q2.queue_id])  # Daily cap = 1
            self.assertEqual(queue.get_item(q_fut.queue_id).status, ArticleStatus.SCHEDULED.value)

            # Error recovery: missing article triggers FAILED + retry increment
            orphan = queue.enqueue(
                Article(id="missing_art", title="Missing"),
                target_blog_id="b1",
                mode=PublishingMode.SCHEDULED,
                scheduled_time="2026-11-22T07:00:00Z",
            )
            repo.save_schedule_config(ScheduleConfig(enabled=True, max_daily_posts=5))
            res2 = scheduler.process_due_jobs(now_utc=now)
            self.assertIn(orphan.queue_id, res2["failed"])
            failed_item = queue.get_item(orphan.queue_id)
            self.assertEqual(failed_item.status, ArticleStatus.FAILED.value)
            self.assertEqual(failed_item.retry_count, 1)

            # Mark for retry resets status back to Scheduled
            queue.mark_for_retry(orphan.queue_id)
            self.assertEqual(queue.get_item(orphan.queue_id).status, ArticleStatus.SCHEDULED.value)


if __name__ == "__main__":
    unittest.main()
