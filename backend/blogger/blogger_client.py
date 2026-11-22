"""Official Google Blogger API v3 client.

Reference: https://developers.google.com/blogger/docs/3.0/getting_started
"""

from __future__ import annotations

from typing import Any

from backend.blogger.oauth import BloggerOAuthManager
from backend.models.schemas import BlogAccount
from backend.utils.errors import BloggerAPIError, BloggerAuthError, BloggerQuotaError
from backend.utils.http_client import HTTPResponse, ResilientHTTPClient


BLOGGER_API_BASE = "https://www.googleapis.com/blogger/v3"


class BloggerClient:
    """REST client for Google Blogger API v3 with automatic token refresh on 401."""

    def __init__(
        self,
        oauth: BloggerOAuthManager,
        *,
        http_client: ResilientHTTPClient | None = None,
    ) -> None:
        self.oauth = oauth
        self.http = http_client or ResilientHTTPClient()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{BLOGGER_API_BASE}{path}"
        token = self.oauth.get_access_token()
        resp = self._send(method, url, token, params=params, json_body=json_body)

        # Retry once with a freshly refreshed token on 401 Unauthorized
        if resp.status_code == 401:
            self.oauth.invalidate()
            token = self.oauth.get_access_token(force_refresh=True)
            resp = self._send(method, url, token, params=params, json_body=json_body)

        if resp.status_code == 401:
            raise BloggerAuthError("Blogger API returned 401 Unauthorized even after token refresh.")
        if resp.status_code in {403, 429}:
            body_lower = resp.text.lower()
            if "quota" in body_lower or "ratelimit" in body_lower or resp.status_code == 429:
                raise BloggerQuotaError(f"Blogger API quota/rate limit exceeded (HTTP {resp.status_code}).")
            raise BloggerAuthError(f"Blogger API access forbidden (HTTP 403): {resp.text[:250]}")
        if resp.status_code >= 400:
            raise BloggerAPIError(
                f"Blogger API error (HTTP {resp.status_code}) on {method} {path}: {resp.text[:300]}",
                retryable=resp.status_code >= 500,
            )

        if resp.status_code == 204 or not resp.body:
            return {}
        return resp.json()

    def _send(
        self,
        method: str,
        url: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        return self.http.request(
            method,
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json_body=json_body,
        )

    def list_blogs(self) -> list[BlogAccount]:
        """Retrieve all Blogger blogs accessible to the authenticated Google account."""
        data = self._request("GET", "/users/self/blogs")
        items = data.get("items") or []
        blogs: list[BlogAccount] = []
        for item in items:
            locale_obj = item.get("locale") or {}
            locale_str = str(locale_obj.get("language") or "en")
            blogs.append(
                BlogAccount(
                    blog_id=str(item.get("id", "")),
                    name=str(item.get("name", "Untitled Blog")),
                    url=str(item.get("url", "")),
                    description=str(item.get("description", "")),
                    locale=locale_str,
                )
            )
        return blogs

    def get_blog(self, blog_id: str) -> BlogAccount:
        """Retrieve metadata for a specific Blogger blog."""
        item = self._request("GET", f"/blogs/{blog_id}")
        locale_obj = item.get("locale") or {}
        return BlogAccount(
            blog_id=str(item.get("id", blog_id)),
            name=str(item.get("name", "Untitled Blog")),
            url=str(item.get("url", "")),
            description=str(item.get("description", "")),
            locale=str(locale_obj.get("language") or "en"),
        )

    def create_post(
        self,
        blog_id: str,
        *,
        title: str,
        content_html: str,
        labels: list[str] | None = None,
        is_draft: bool = False,
        scheduled_published_rfc3339: str | None = None,
    ) -> dict[str, Any]:
        """Create a Blogger post (live, draft, or scheduled via RFC 3339 published date)."""
        body: dict[str, Any] = {
            "kind": "blogger#post",
            "blog": {"id": blog_id},
            "title": title,
            "content": content_html,
        }
        if labels:
            body["labels"] = labels
        if scheduled_published_rfc3339:
            body["published"] = scheduled_published_rfc3339

        params: dict[str, Any] = {"isDraft": "true" if is_draft else "false"}
        return self._request("POST", f"/blogs/{blog_id}/posts", params=params, json_body=body)

    def update_post(
        self,
        blog_id: str,
        post_id: str,
        *,
        title: str,
        content_html: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing Blogger post."""
        body: dict[str, Any] = {
            "kind": "blogger#post",
            "id": post_id,
            "blog": {"id": blog_id},
            "title": title,
            "content": content_html,
        }
        if labels is not None:
            body["labels"] = labels
        return self._request("PATCH", f"/blogs/{blog_id}/posts/{post_id}", json_body=body)

    def delete_post(self, blog_id: str, post_id: str) -> None:
        """Delete a Blogger post."""
        self._request("DELETE", f"/blogs/{blog_id}/posts/{post_id}")

    def publish_draft(
        self,
        blog_id: str,
        post_id: str,
        *,
        publish_date_rfc3339: str | None = None,
    ) -> dict[str, Any]:
        """Publish an existing draft immediately or schedule it using publishDate."""
        params: dict[str, Any] = {}
        if publish_date_rfc3339:
            params["publishDate"] = publish_date_rfc3339
        return self._request("POST", f"/blogs/{blog_id}/posts/{post_id}/publish", params=params or None)

    def list_posts(
        self,
        blog_id: str,
        *,
        status: list[str] | None = None,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        """Retrieve posts for a blog (live, draft, or scheduled)."""
        params: dict[str, Any] = {"maxResults": max(1, min(max_results, 100))}
        if status:
            params["status"] = status
        data = self._request("GET", f"/blogs/{blog_id}/posts", params=params)
        return list(data.get("items") or [])
