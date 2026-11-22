"""Pexels API image provider."""

from __future__ import annotations

from backend.images.base import ImageProvider
from backend.models.schemas import ImageAsset
from backend.utils.errors import ImageProviderError
from backend.utils.http_client import ResilientHTTPClient


PEXELS_API_URL = "https://api.pexels.com/v1/search"


class PexelsProvider(ImageProvider):
    provider_name = "Pexels"

    def __init__(self, api_key: str = "", *, http_client: ResilientHTTPClient | None = None) -> None:
        self.api_key = api_key.strip()
        self.http = http_client or ResilientHTTPClient()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, *, limit: int = 8) -> list[ImageAsset]:
        if not self.is_configured():
            return []
        try:
            resp = self.http.get(
                PEXELS_API_URL,
                headers={"Authorization": self.api_key},
                params={"query": query, "per_page": max(1, min(limit, 20))},
            )
        except Exception as exc:
            raise ImageProviderError(f"Pexels request failed: {exc}") from exc

        if resp.status_code in {401, 403}:
            raise ImageProviderError("Pexels API authentication failed. Verify PEXELS_API_KEY.", retryable=False)
        if resp.status_code >= 400:
            raise ImageProviderError(f"Pexels returned HTTP {resp.status_code}")

        photos = resp.json().get("photos") or []
        assets: list[ImageAsset] = []
        for photo in photos:
            src = photo.get("src") or {}
            original_url = str(src.get("large") or src.get("original") or "").strip()
            if not original_url:
                continue
            assets.append(
                ImageAsset(
                    id=str(photo.get("id") or original_url),
                    title=str(photo.get("alt") or f"Pexels photo {photo.get('id')}").strip(),
                    original_url=original_url,
                    preview_url=str(src.get("medium") or original_url).strip(),
                    creator_name=str(photo.get("photographer") or "Pexels Photographer").strip(),
                    source_provider=self.provider_name,
                    license_name="Pexels License",
                    license_url="https://www.pexels.com/license/",
                    attribution_required=False,
                    attribution_text="",
                    commercial_use_permitted=True,
                    width=photo.get("width"),
                    height=photo.get("height"),
                )
            )
        return assets
