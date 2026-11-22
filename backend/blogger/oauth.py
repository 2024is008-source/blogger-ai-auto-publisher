"""Google OAuth 2.0 token manager for Google Blogger API v3.

Uses long-lived refresh tokens stored exclusively in GitHub Secrets and
automatically refreshes short-lived access tokens with expiration buffering.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from backend.utils.errors import BloggerAuthError, ConfigurationError
from backend.utils.http_client import ResilientHTTPClient


GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
BLOGGER_OAUTH_SCOPE = "https://www.googleapis.com/auth/blogger"


@dataclass
class AccessToken:
    token: str
    expires_at: float
    scope: str = BLOGGER_OAUTH_SCOPE

    def is_expired(self, skew_seconds: int = 60) -> bool:
        return time.time() >= (self.expires_at - skew_seconds)


class BloggerOAuthManager:
    """Manages OAuth 2.0 token refresh and expiration for Blogger API v3."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        http_client: ResilientHTTPClient | None = None,
    ) -> None:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()
        self.http = http_client or ResilientHTTPClient()
        self._cached_token: AccessToken | None = None

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid OAuth access token, refreshing if missing or near expiration."""
        if not force_refresh and self._cached_token and not self._cached_token.is_expired():
            return self._cached_token.token
        return self.refresh_access_token().token

    def refresh_access_token(self) -> AccessToken:
        """Exchange the configured refresh token for a fresh Google OAuth access token."""
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise ConfigurationError(
                "Missing Google OAuth credentials. Configure GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and BLOGGER_REFRESH_TOKEN in GitHub Secrets."
            )

        try:
            resp = self.http.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        except Exception as exc:
            raise BloggerAuthError(f"Network error refreshing Google OAuth token: {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            error_detail = ""
            try:
                payload = resp.json()
                error_detail = f"{payload.get('error', '')}: {payload.get('error_description', '')}".strip(": ")
            except Exception:
                error_detail = resp.text[:200]
            raise BloggerAuthError(
                f"Failed to refresh Blogger OAuth token (HTTP {resp.status_code}): {error_detail}. "
                "Re-run scripts/setup_blogger_oauth.py to issue a new BLOGGER_REFRESH_TOKEN.",
                retryable=resp.status_code >= 500,
            )

        data = resp.json()
        access_token = str(data.get("access_token") or "").strip()
        expires_in = int(data.get("expires_in") or 3600)
        scope = str(data.get("scope") or BLOGGER_OAUTH_SCOPE)

        if not access_token:
            raise BloggerAuthError("OAuth token endpoint returned no access_token.")

        self._cached_token = AccessToken(
            token=access_token,
            expires_at=time.time() + expires_in,
            scope=scope,
        )
        return self._cached_token

    def invalidate(self) -> None:
        """Force the next request to obtain a fresh access token."""
        self._cached_token = None
