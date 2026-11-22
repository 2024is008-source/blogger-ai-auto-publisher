"""Pixabay API image provider."""

from __future__ import annotations

from backend.images.base import ImageProvider
from backend.models.schemas import ImageAsset
from backend.utils.errors import ImageProviderError
from backend.utils.http_client import ResilientHTTPClient


PIXABAY_API_URL = "https://pixabay.com/api/"


class PixabayProvider(ImageProvider):
    provider_name = "Pixabay"

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
                PIXABAY_API_URL,
                params={
                    "key": self.api_key,
                    "q": query,
                    "image_type": "photo",
                    "safesearch": "true",
                    "per_page": max(3, min(limit, 20)),
                },
            )
        except Exception as exc:
            raise ImageProviderError(f"Pixabay request failed: {exc}") from exc

        if resp.status_code in {400, 401, 403}:
            raise ImageProviderError("Pixabay API authentication or request error. Verify PIXABAY_API_KEY.", retryable=False)
        if resp.status_code >= 400:
            raise ImageProviderError(f"Pixabay returned HTTP {resp.status_code}")

        hits = resp.json().get("hits") or []
        assets: list[ImageAsset] = []
        for hit in hits:
            original_url = str(hit.get("largeImageURL") or hit.get("webformatURL") or "").strip()
            if not original_url:
                continue
            assets.append(
                ImageAsset(
                    id=str(hit.get("id") or original_url),
                    title=str(hit.get("tags") or f"Pixabay photo {hit.get('id')}").strip(),
                    original_url=original_url,
                    preview_url=str(hit.get("previewURL") or hit.get("webformatURL") or original_url).strip(),
                    creator_name=str(hit.get("user") or "Pixabay Contributor").strip(),
                    source_provider=self.provider_name,
                    license_name="Pixabay Content License",
                    license_url="https://pixabay.com/service/license-summary/",
                    attribution_required=False,
                    attribution_text="",
                    commercial_use_permitted=True,
                    width=hit.get("imageWidth"),
                    height=hit.get("imageHeight"),
                )
            )
        return assets
