"""Authorized image hosting adapters for Blogger-compatible public image URLs.

Blogger API v3 does not provide a general-purpose media upload endpoint.
This module supports authorized hosting via Cloudinary or GitHub repository
asset hosting, verifies public URL accessibility, and explicitly reports
missing configuration rather than pretending an upload succeeded.
"""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import urlparse

from backend.config import AppConfig
from backend.models.schemas import ImageAsset
from backend.utils.errors import ImageProviderError, ImageUploadConfigError
from backend.utils.http_client import ResilientHTTPClient


class ImageUploader:
    """Uploads permitted images to an authorized host and verifies accessibility."""

    def __init__(self, config: AppConfig, http_client: ResilientHTTPClient | None = None) -> None:
        self.config = config
        self.http = http_client or ResilientHTTPClient(
            timeout=config.http_timeout_seconds,
            max_retries=config.max_retries,
        )

    def upload(self, asset: ImageAsset) -> str:
        """Upload an asset via the configured authorized host and return its public URL."""
        provider = self.config.image_host_provider
        if provider == "cloudinary":
            url = self._upload_cloudinary(asset)
        elif provider == "github":
            url = self._upload_github_repo(asset)
        else:
            raise ImageUploadConfigError(
                "No authorized image hosting provider is configured. "
                "Set IMAGE_HOST_PROVIDER to 'cloudinary' (with CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET) "
                "or 'github' (with GITHUB_IMAGE_REPO and GITHUB_TOKEN) in GitHub Secrets/Variables."
            )

        self.verify_public_url(url)
        asset.hosted_url = url
        return url

    def verify_public_url(self, url: str) -> None:
        """Confirm that a hosted image URL is publicly reachable and serves an image."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ImageProviderError(f"Hosted image URL is invalid: {url}", retryable=False)
        try:
            resp = self.http.head(url)
            if resp.status_code == 405:
                resp = self.http.get(url)
        except Exception as exc:
            raise ImageProviderError(f"Failed verifying hosted image URL {url}: {exc}") from exc

        if resp.status_code >= 400:
            raise ImageProviderError(
                f"Hosted image URL {url} is not accessible (HTTP {resp.status_code}).",
                retryable=resp.status_code >= 500,
            )

    def _download_bytes(self, url: str) -> tuple[bytes, str]:
        try:
            resp = self.http.get(url)
        except Exception as exc:
            raise ImageProviderError(f"Failed downloading image from {url}: {exc}") from exc
        if resp.status_code >= 400 or not resp.body:
            raise ImageProviderError(f"Image download failed (HTTP {resp.status_code}) for {url}")
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
        ext = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }.get(content_type, "jpg")
        return resp.body, ext

    def _upload_cloudinary(self, asset: ImageAsset) -> str:
        if not (self.config.cloudinary_cloud_name and self.config.cloudinary_upload_preset):
            raise ImageUploadConfigError(
                "Cloudinary is selected (IMAGE_HOST_PROVIDER=cloudinary) but "
                "CLOUDINARY_CLOUD_NAME or CLOUDINARY_UPLOAD_PRESET is missing."
            )
        endpoint = f"https://api.cloudinary.com/v1_1/{self.config.cloudinary_cloud_name}/image/upload"
        resp = self.http.post(
            endpoint,
            data={
                "file": asset.original_url,
                "upload_preset": self.config.cloudinary_upload_preset,
            },
        )
        if resp.status_code >= 400:
            raise ImageProviderError(f"Cloudinary upload failed (HTTP {resp.status_code}): {resp.text[:200]}")
        secure_url = str(resp.json().get("secure_url") or "").strip()
        if not secure_url:
            raise ImageProviderError("Cloudinary response did not include secure_url.")
        return secure_url

    def _upload_github_repo(self, asset: ImageAsset) -> str:
        if not (self.config.github_image_repo and self.config.github_token):
            raise ImageUploadConfigError(
                "GitHub image hosting is selected (IMAGE_HOST_PROVIDER=github) but "
                "GITHUB_IMAGE_REPO or GITHUB_TOKEN is missing."
            )
        raw_bytes, ext = self._download_bytes(asset.original_url)
        digest = hashlib.sha256(raw_bytes).hexdigest()[:16]
        path = f"assets/images/{asset.source_provider.lower().replace(' ', '-')}-{digest}.{ext}"
        api_url = f"https://api.github.com/repos/{self.config.github_image_repo}/contents/{path}"
        encoded = base64.b64encode(raw_bytes).decode("ascii")

        resp = self.http.put(
            api_url,
            headers={
                "Authorization": f"Bearer {self.config.github_token}",
                "Accept": "application/vnd.github+json",
            },
            json_body={
                "message": f"Add licensed image asset {digest} ({asset.source_provider})",
                "content": encoded,
                "branch": self.config.github_image_branch,
            },
        )
        if resp.status_code not in {200, 201, 422}:
            raise ImageProviderError(f"GitHub image upload failed (HTTP {resp.status_code}): {resp.text[:200]}")
        return (
            f"https://raw.githubusercontent.com/{self.config.github_image_repo}/"
            f"{self.config.github_image_branch}/{path}"
        )
