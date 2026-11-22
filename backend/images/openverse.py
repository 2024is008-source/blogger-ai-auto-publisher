"""Openverse API v1 image provider."""

from __future__ import annotations

from backend.images.base import ImageProvider
from backend.models.schemas import ImageAsset
from backend.utils.errors import ImageProviderError
from backend.utils.http_client import ResilientHTTPClient


OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"


class OpenverseProvider(ImageProvider):
    provider_name = "Openverse"

    def __init__(self, *, enabled: bool = True, http_client: ResilientHTTPClient | None = None) -> None:
        self.enabled = enabled
        self.http = http_client or ResilientHTTPClient()

    def is_configured(self) -> bool:
        return self.enabled

    def search(self, query: str, *, limit: int = 8) -> list[ImageAsset]:
        if not self.is_configured():
            return []
        try:
            resp = self.http.get(
                OPENVERSE_API_URL,
                params={"q": query, "page_size": max(1, min(limit, 20))},
            )
        except Exception as exc:
            raise ImageProviderError(f"Openverse request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise ImageProviderError(f"Openverse returned HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        results = data.get("results") or []
        assets: list[ImageAsset] = []
        for item in results:
            original_url = str(item.get("url") or "").strip()
            if not original_url:
                continue
            license_code = str(item.get("license") or "").strip()
            license_version = str(item.get("license_version") or "").strip()
            license_label = f"CC-{license_code.upper()} {license_version}".strip() if license_code and license_code.lower() not in {"cc0", "pdm"} else license_code
            assets.append(
                ImageAsset(
                    id=str(item.get("id") or original_url),
                    title=str(item.get("title") or query).strip(),
                    original_url=original_url,
                    preview_url=str(item.get("thumbnail") or original_url).strip(),
                    creator_name=str(item.get("creator") or "Unknown creator").strip(),
                    source_provider=self.provider_name,
                    license_name=license_label,
                    license_url=str(item.get("license_url") or "").strip(),
                    attribution_required=license_code.lower() not in {"cc0", "pdm"},
                    attribution_text=str(item.get("attribution") or "").strip(),
                    width=item.get("width"),
                    height=item.get("height"),
                )
            )
        return assets
