"""Wikimedia Commons API image provider with per-file extmetadata license extraction."""

from __future__ import annotations

import re

from backend.images.base import ImageProvider
from backend.models.schemas import ImageAsset
from backend.utils.errors import ImageProviderError
from backend.utils.http_client import ResilientHTTPClient


WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


class WikimediaCommonsProvider(ImageProvider):
    provider_name = "Wikimedia Commons"

    def __init__(self, *, enabled: bool = True, http_client: ResilientHTTPClient | None = None) -> None:
        self.enabled = enabled
        self.http = http_client or ResilientHTTPClient()

    def is_configured(self) -> bool:
        return self.enabled

    def search(self, query: str, *, limit: int = 8) -> list[ImageAsset]:
        if not self.is_configured():
            return []
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": max(1, min(limit, 20)),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": 640,
        }
        try:
            resp = self.http.get(WIKIMEDIA_API_URL, params=params)
        except Exception as exc:
            raise ImageProviderError(f"Wikimedia Commons request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise ImageProviderError(f"Wikimedia Commons returned HTTP {resp.status_code}")

        pages = ((resp.json().get("query") or {}).get("pages") or {}).values()
        assets: list[ImageAsset] = []
        for page in pages:
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            ext = info.get("extmetadata") or {}
            original_url = str(info.get("url") or "").strip()
            if not original_url:
                continue
            license_short = _strip_tags((ext.get("LicenseShortName") or {}).get("value", ""))
            license_url = _strip_tags((ext.get("LicenseUrl") or {}).get("value", ""))
            artist = _strip_tags((ext.get("Artist") or {}).get("value", "")) or "Wikimedia Contributor"
            title = _strip_tags((ext.get("ObjectName") or {}).get("value", "")) or str(page.get("title") or query).replace("File:", "")

            assets.append(
                ImageAsset(
                    id=str(page.get("pageid") or original_url),
                    title=title,
                    original_url=original_url,
                    preview_url=str(info.get("thumburl") or original_url).strip(),
                    creator_name=artist,
                    source_provider=self.provider_name,
                    license_name=license_short,
                    license_url=license_url,
                    attribution_required=True,
                    attribution_text="",
                    width=info.get("width"),
                    height=info.get("height"),
                )
            )
        return assets
