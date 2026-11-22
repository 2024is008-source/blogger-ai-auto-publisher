"""Image discovery orchestrator: multi-provider search, license filtering, upload, and HTML injection."""

from __future__ import annotations

import html
from bs4 import BeautifulSoup

from backend.config import AppConfig
from backend.images.base import ImageProvider
from backend.images.license_checker import validate_and_enrich_asset
from backend.images.openverse import OpenverseProvider
from backend.images.pexels import PexelsProvider
from backend.images.pixabay import PixabayProvider
from backend.images.uploader import ImageUploader
from backend.images.wikimedia import WikimediaCommonsProvider
from backend.models.schemas import Article, ImageAsset, LicenseFilter
from backend.storage.repository import RepositoryStorage
from backend.utils.errors import ImageProviderError, InvalidLicenseError
from backend.utils.http_client import ResilientHTTPClient
from backend.utils.logger import StructuredLogger


class ImageManager:
    """Coordinates modular image providers, strict license checks, hosting, and HTML insertion."""

    def __init__(
        self,
        config: AppConfig,
        *,
        providers: list[ImageProvider] | None = None,
        uploader: ImageUploader | None = None,
        repository: RepositoryStorage | None = None,
        http_client: ResilientHTTPClient | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        self.config = config
        self.http = http_client or ResilientHTTPClient(
            timeout=config.http_timeout_seconds,
            max_retries=config.max_retries,
        )
        self.providers: list[ImageProvider] = providers if providers is not None else [
            OpenverseProvider(enabled=config.openverse_enabled, http_client=self.http),
            WikimediaCommonsProvider(enabled=config.wikimedia_enabled, http_client=self.http),
            PexelsProvider(api_key=config.pexels_api_key, http_client=self.http),
            PixabayProvider(api_key=config.pixabay_api_key, http_client=self.http),
        ]
        self.uploader = uploader or ImageUploader(config, http_client=self.http)
        self.repository = repository
        self.logger = logger or StructuredLogger()

    def register_provider(self, provider: ImageProvider) -> None:
        """Register an additional modular image provider."""
        self.providers.append(provider)

    def search_permitted_images(
        self,
        query: str,
        *,
        license_filter: LicenseFilter = LicenseFilter.COMMERCIAL_PERMITTED,
        limit_per_provider: int = 6,
        provider_names: list[str] | None = None,
    ) -> list[ImageAsset]:
        """Search configured providers and return only license-verified assets."""
        allowed_names = {p.lower() for p in provider_names} if provider_names else None
        verified: list[ImageAsset] = []
        seen_urls: set[str] = set()

        for provider in self.providers:
            if not provider.is_configured():
                continue
            if allowed_names and provider.provider_name.lower() not in allowed_names:
                continue
            try:
                candidates = provider.search(query, limit=limit_per_provider)
            except ImageProviderError as exc:
                self.logger.warning(
                    "image_manager",
                    f"Provider {provider.provider_name} unavailable; continuing with remaining providers.",
                    error=str(exc),
                )
                continue

            for asset in candidates:
                if asset.original_url in seen_urls:
                    continue
                try:
                    enriched = validate_and_enrich_asset(asset, license_filter)
                    verified.append(enriched)
                    seen_urls.add(enriched.original_url)
                except InvalidLicenseError:
                    continue

        return verified

    def build_figure_html(self, asset: ImageAsset, *, use_hosted_url: bool = True) -> str:
        """Render clean Blogger-compatible <figure> HTML with alt text, dimensions, and attribution."""
        img_url = asset.hosted_url if (use_hosted_url and asset.hosted_url) else asset.original_url
        alt = html.escape(asset.alt_text or asset.title or "Article illustration", quote=True)
        src = html.escape(img_url, quote=True)
        dims = ""
        if asset.width and asset.height:
            dims = f' width="{int(asset.width)}" height="{int(asset.height)}"'

        caption_html = ""
        if asset.attribution_required or asset.attribution_text:
            lic_url = html.escape(asset.license_url, quote=True)
            creator = html.escape(asset.creator_name or "Unknown creator")
            provider = html.escape(asset.source_provider)
            lic_name = html.escape(asset.license_name)
            caption_html = (
                f'<figcaption style="font-size:0.85em;color:#475569;margin-top:6px;">'
                f'Image by {creator} via {provider} '
                f'(<a href="{lic_url}" rel="noopener noreferrer" target="_blank">{lic_name}</a>)'
                f"</figcaption>"
            )

        return (
            f'<figure style="margin:24px 0;text-align:center;">'
            f'<img src="{src}" alt="{alt}"{dims} loading="lazy" style="max-width:100%;height:auto;border-radius:8px;" />'
            f"{caption_html}</figure>"
        )

    def attach_images_to_article(
        self,
        article: Article,
        assets: list[ImageAsset],
        *,
        upload_to_host: bool = False,
    ) -> Article:
        """Attach validated images to an article, optionally uploading them first, and inject HTML."""
        if not assets:
            return article

        prepared: list[ImageAsset] = []
        for idx, asset in enumerate(assets):
            if not asset.alt_text and idx < len(article.image_alt_texts):
                asset.alt_text = article.image_alt_texts[idx]
            if upload_to_host:
                self.uploader.upload(asset)
            prepared.append(asset)

        soup = BeautifulSoup(article.html_content or "", "html.parser")
        h2_nodes = soup.find_all("h2")
        for idx, asset in enumerate(prepared):
            fig = BeautifulSoup(self.build_figure_html(asset, use_hosted_url=upload_to_host), "html.parser")
            if idx < len(h2_nodes):
                h2_nodes[idx].insert_before(fig)
            else:
                soup.append(fig)

        article.html_content = str(soup)
        article.images = prepared
        if self.repository:
            self.repository.record_image_licenses(prepared)
        return article
