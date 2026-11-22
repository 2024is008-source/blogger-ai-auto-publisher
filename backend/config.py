"""Centralized configuration loader for Blogger AI Auto Publisher.

All sensitive credentials are loaded exclusively from environment variables
(populated via GitHub Secrets in GitHub Actions). Never hardcode secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration resolved from environment variables."""

    # Paths
    root_dir: Path = field(default_factory=lambda: Path(os.getenv("BAAP_ROOT_DIR", ".")).resolve())
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("BAAP_DATA_DIR", "data")).resolve())

    # Gemini AI
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    )

    # Google Blogger OAuth 2.0
    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", "").strip())
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", "").strip())
    blogger_refresh_token: str = field(default_factory=lambda: os.getenv("BLOGGER_REFRESH_TOKEN", "").strip())
    blogger_blog_id: str = field(default_factory=lambda: os.getenv("BLOGGER_BLOG_ID", "").strip())

    # Image providers
    openverse_enabled: bool = field(
        default_factory=lambda: os.getenv("OPENVERSE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    )
    wikimedia_enabled: bool = field(
        default_factory=lambda: os.getenv("WIKIMEDIA_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    )
    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", "").strip())
    pixabay_api_key: str = field(default_factory=lambda: os.getenv("PIXABAY_API_KEY", "").strip())

    # Image hosting / upload integration
    image_host_provider: str = field(default_factory=lambda: os.getenv("IMAGE_HOST_PROVIDER", "none").strip().lower())
    cloudinary_cloud_name: str = field(default_factory=lambda: os.getenv("CLOUDINARY_CLOUD_NAME", "").strip())
    cloudinary_upload_preset: str = field(default_factory=lambda: os.getenv("CLOUDINARY_UPLOAD_PRESET", "").strip())
    github_image_repo: str = field(default_factory=lambda: os.getenv("GITHUB_IMAGE_REPO", "").strip())
    github_image_branch: str = field(default_factory=lambda: os.getenv("GITHUB_IMAGE_BRANCH", "main").strip())
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", "").strip())

    # Optional Supabase persistence
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", "").strip().rstrip("/"))
    supabase_service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())

    # Runtime flags
    integration_test_mode: bool = field(
        default_factory=lambda: os.getenv("INTEGRATION_TEST_MODE", "false").strip().lower() in {"1", "true", "yes"}
    )
    http_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("HTTP_TIMEOUT_SECONDS", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("HTTP_MAX_RETRIES", "3")))

    def sensitive_values(self) -> list[str]:
        """Return non-empty secret strings for redaction in logs."""
        candidates = [
            self.gemini_api_key,
            self.google_client_secret,
            self.blogger_refresh_token,
            self.pexels_api_key,
            self.pixabay_api_key,
            self.github_token,
            self.supabase_service_role_key,
        ]
        return [v for v in candidates if v and len(v) >= 4]

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def has_blogger_oauth(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.blogger_refresh_token)
