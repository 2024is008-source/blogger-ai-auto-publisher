"""Tests for Blogger OAuth 2.0 refresh, Blogger API v3 client, publishing, and duplicate prevention."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.blogger.blogger_client import BloggerClient
from backend.blogger.oauth import BloggerOAuthManager
from backend.blogger.publisher import BloggerPublisher
from backend.models.schemas import Article, ArticleStatus, BlogAccount, PublishingMode
from backend.storage.repository import RepositoryStorage
from backend.utils.errors import BloggerAPIError, DuplicateArticleError
from backend.utils.http_client import HTTPResponse, ResilientHTTPClient


class TestBloggerOAuthAndPublisher(unittest.TestCase):
    def test_oauth_refresh_and_401_retry(self) -> None:
        calls = {"token": 0, "blogs": 0}

        def transport(**kwargs):
            if "oauth2.googleapis.com/token" in kwargs["url"]:
                calls["token"] += 1
                return HTTPResponse(
                    200,
                    json.dumps({"access_token": f"tok_{calls['token']}", "expires_in": 3600}).encode(),
                    {},
                )
            if "/users/self/blogs" in kwargs["url"]:
                calls["blogs"] += 1
                if calls["blogs"] == 1:
                    return HTTPResponse(401, b'{"error":"invalid_token"}', {})
                return HTTPResponse(
                    200,
                    json.dumps(
                        {"items": [{"id": "12345", "name": "Tech Blog", "url": "https://tech.blogspot.com"}]}
                    ).encode(),
                    {},
                )
            return HTTPResponse(404, b"", {})

        http = ResilientHTTPClient(transport=transport, max_retries=0)
        oauth = BloggerOAuthManager(
            client_id="cid", client_secret="csec", refresh_token="rtok", http_client=http
        )
        client = BloggerClient(oauth, http_client=http)
        blogs = client.list_blogs()

        self.assertEqual(len(blogs), 1)
        self.assertEqual(blogs[0].blog_id, "12345")
        self.assertEqual(calls["token"], 2)  # Initial fetch + refresh after 401

    def test_draft_live_scheduled_and_duplicate_prevention(self) -> None:
        def transport(**kwargs):
            if "oauth2.googleapis.com/token" in kwargs["url"]:
                return HTTPResponse(200, json.dumps({"access_token": "tok", "expires_in": 3600}).encode(), {})
            if "/posts" in kwargs["url"] and kwargs["method"] == "POST":
                body = json.loads(kwargs["body"].decode("utf-8"))
                is_draft = "isDraft=true" in kwargs["url"]
                status = "DRAFT" if is_draft else ("SCHEDULED" if "published" in body else "LIVE")
                return HTTPResponse(
                    200,
                    json.dumps(
                        {
                            "id": "post_999",
                            "status": status,
                            "url": "https://tech.blogspot.com/2026/11/post.html",
                        }
                    ).encode(),
                    {},
                )
            return HTTPResponse(404, b"", {})

        http = ResilientHTTPClient(transport=transport, max_retries=0)
        oauth = BloggerOAuthManager(client_id="c", client_secret="s", refresh_token="r", http_client=http)
        client = BloggerClient(oauth, http_client=http)

        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositoryStorage(Path(tmp))
            repo.upsert_blog(BlogAccount(blog_id="blog_a", name="Blog A", url="https://a.blogspot.com"))
            repo.upsert_blog(BlogAccount(blog_id="blog_b", name="Blog B", url="https://b.blogspot.com"))
            publisher = BloggerPublisher(client, repo)

            article = Article(id="art_1", title="Test Post", html_content="<p>Hello world</p>", main_keyword="test")

            # 1. Draft creation
            draft_rec = publisher.publish_article(article, blog_id="blog_a", mode=PublishingMode.DRAFT)
            self.assertEqual(draft_rec.status, ArticleStatus.DRAFT.value)

            # 2. Live publication to Blog A
            live_rec = publisher.publish_article(article, blog_id="blog_a", mode=PublishingMode.MANUAL)
            self.assertEqual(live_rec.status, ArticleStatus.PUBLISHED.value)
            self.assertEqual(live_rec.blogger_post_id, "post_999")

            # 3. Duplicate to same blog must be blocked
            with self.assertRaises(DuplicateArticleError):
                publisher.publish_article(article, blog_id="blog_a", mode=PublishingMode.MANUAL)

            # 4. Scheduled publication to Blog B (multi-blog) must succeed with UTC conversion
            sched_rec = publisher.publish_article(
                article,
                blog_id="blog_b",
                mode=PublishingMode.SCHEDULED,
                scheduled_time="2026-12-01T09:00:00",
                timezone_name="Asia/Colombo",
            )
            self.assertEqual(sched_rec.status, ArticleStatus.SCHEDULED.value)

    def test_unconfirmed_live_status_is_rejected(self) -> None:
        def transport(**kwargs):
            if "oauth2.googleapis.com/token" in kwargs["url"]:
                return HTTPResponse(200, json.dumps({"access_token": "tok", "expires_in": 3600}).encode(), {})
            return HTTPResponse(200, json.dumps({"id": "post_1", "status": "DRAFT"}).encode(), {})

        http = ResilientHTTPClient(transport=transport, max_retries=0)
        oauth = BloggerOAuthManager(client_id="c", client_secret="s", refresh_token="r", http_client=http)
        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositoryStorage(Path(tmp))
            publisher = BloggerPublisher(BloggerClient(oauth, http_client=http), repo)
            article = Article(id="art_bad", title="Bad Status", html_content="<p>Body</p>")
            with self.assertRaises(BloggerAPIError):
                publisher.publish_article(article, blog_id="blog_a", mode=PublishingMode.MANUAL)


if __name__ == "__main__":
    unittest.main()
