"""Tests for modular image providers, asset-level license verification, and authorized uploader."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.config import AppConfig
from backend.images.image_manager import ImageManager
from backend.images.license_checker import validate_and_enrich_asset
from backend.images.openverse import OpenverseProvider
from backend.images.pexels import PexelsProvider
from backend.images.pixabay import PixabayProvider
from backend.images.uploader import ImageUploader
from backend.images.wikimedia import WikimediaCommonsProvider
from backend.models.schemas import Article, ImageAsset, LicenseFilter
from backend.storage.repository import RepositoryStorage
from backend.utils.errors import ImageUploadConfigError, InvalidLicenseError
from backend.utils.http_client import HTTPResponse, ResilientHTTPClient


class TestImagesAndLicenses(unittest.TestCase):
    def test_asset_level_license_filtering_rejects_nc_and_unknown(self) -> None:
        nc_asset = ImageAsset(
            id="1",
            title="NC Image",
            original_url="https://example.org/nc.jpg",
            preview_url="https://example.org/nc_thumb.jpg",
            creator_name="Alice",
            source_provider="Openverse",
            license_name="CC-BY-NC 4.0",
            license_url="https://creativecommons.org/licenses/by-nc/4.0/",
            attribution_required=True,
            attribution_text="",
        )
        with self.assertRaises(InvalidLicenseError):
            validate_and_enrich_asset(nc_asset, LicenseFilter.COMMERCIAL_PERMITTED)

        unknown_asset = ImageAsset(
            id="2",
            title="Unknown",
            original_url="https://example.org/unk.jpg",
            preview_url="https://example.org/unk.jpg",
            creator_name="Bob",
            source_provider="Wikimedia Commons",
            license_name="All Rights Reserved",
            license_url="",
            attribution_required=True,
            attribution_text="",
        )
        with self.assertRaises(InvalidLicenseError):
            validate_and_enrich_asset(unknown_asset, LicenseFilter.ALL_SUPPORTED)

        cc0_asset = ImageAsset(
            id="3",
            title="Public Domain Herb",
            original_url="https://example.org/cc0.jpg",
            preview_url="https://example.org/cc0.jpg",
            creator_name="Carol",
            source_provider="Openverse",
            license_name="cc0",
            license_url="",
            attribution_required=False,
            attribution_text="",
        )
        enriched = validate_and_enrich_asset(cc0_asset, LicenseFilter.CC0_PUBLIC_DOMAIN)
        self.assertTrue(enriched.commercial_use_permitted)
        self.assertFalse(enriched.attribution_required)
        self.assertIn("creativecommons.org/publicdomain/zero", enriched.license_url)

    def test_all_four_providers_and_manager_filter(self) -> None:
        def transport(**kwargs):
            url = kwargs["url"]
            if "api.openverse.org" in url:
                payload = {
                    "results": [
                        {
                            "id": "ov1",
                            "title": "Basil Plant",
                            "url": "https://img.example/ov1.jpg",
                            "thumbnail": "https://img.example/ov1_t.jpg",
                            "creator": "OpenArtist",
                            "license": "by",
                            "license_version": "4.0",
                            "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        },
                        {
                            "id": "ov2",
                            "title": "NonCommercial Photo",
                            "url": "https://img.example/ov2.jpg",
                            "license": "by-nc",
                            "license_version": "4.0",
                        },
                    ]
                }
            elif "commons.wikimedia.org" in url:
                payload = {
                    "query": {
                        "pages": {
                            "101": {
                                "pageid": 101,
                                "title": "File:Mint_leaf.jpg",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/mint.jpg",
                                        "thumburl": "https://upload.wikimedia.org/mint_t.jpg",
                                        "width": 1200,
                                        "height": 800,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
                                            "Artist": {"value": "<span>WikiUser</span>"},
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            elif "api.pexels.com" in url:
                payload = {
                    "photos": [
                        {
                            "id": 555,
                            "alt": "Kitchen herbs",
                            "photographer": "PexelsPro",
                            "width": 1600,
                            "height": 1000,
                            "src": {"large": "https://images.pexels.com/555.jpg", "medium": "https://images.pexels.com/555_m.jpg"},
                        }
                    ]
                }
            elif "pixabay.com" in url:
                payload = {
                    "hits": [
                        {
                            "id": 888,
                            "tags": "rosemary, pot",
                            "user": "PixCreator",
                            "imageWidth": 1280,
                            "imageHeight": 720,
                            "largeImageURL": "https://cdn.pixabay.com/888.jpg",
                            "previewURL": "https://cdn.pixabay.com/888_p.jpg",
                        }
                    ]
                }
            else:
                payload = {}
            return HTTPResponse(200, json.dumps(payload).encode("utf-8"), {})

        http = ResilientHTTPClient(transport=transport, max_retries=0)
        cfg = AppConfig(pexels_api_key="px-key", pixabay_api_key="pb-key")
        providers = [
            OpenverseProvider(enabled=True, http_client=http),
            WikimediaCommonsProvider(enabled=True, http_client=http),
            PexelsProvider(api_key="px-key", http_client=http),
            PixabayProvider(api_key="pb-key", http_client=http),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            repo = RepositoryStorage(Path(tmp))
            mgr = ImageManager(cfg, providers=providers, repository=repo, http_client=http)
            results = mgr.search_permitted_images("herbs", license_filter=LicenseFilter.COMMERCIAL_PERMITTED)
            # ov2 (by-nc) must be filtered out; 4 commercial-permitted assets remain
            self.assertEqual(len(results), 4)
            providers_found = {r.source_provider for r in results}
            self.assertEqual(providers_found, {"Openverse", "Wikimedia Commons", "Pexels", "Pixabay"})

            article = Article(title="Herbs", html_content="<p>Intro</p><h2>Section 1</h2><p>Body</p>")
            mgr.attach_images_to_article(article, results[:1], upload_to_host=False)
            self.assertIn("<figure", article.html_content)
            self.assertIn("Openverse", article.html_content)
            self.assertEqual(len(repo.list_image_licenses()), 1)

    def test_uploader_reports_missing_config_and_supports_cloudinary(self) -> None:
        asset = ImageAsset(
            id="ov1",
            title="Test",
            original_url="https://img.example/ov1.jpg",
            preview_url="https://img.example/ov1.jpg",
            creator_name="Alice",
            source_provider="Openverse",
            license_name="CC0 1.0 Public Domain",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            attribution_required=False,
            attribution_text="",
        )
        # Missing config must raise explicit ImageUploadConfigError
        uploader_none = ImageUploader(AppConfig(image_host_provider="none"))
        with self.assertRaises(ImageUploadConfigError):
            uploader_none.upload(asset)

        # Configured Cloudinary upload + public URL HEAD verification
        def transport(**kwargs):
            if kwargs["method"] == "POST" and "api.cloudinary.com" in kwargs["url"]:
                return HTTPResponse(200, json.dumps({"secure_url": "https://res.cloudinary.com/demo/herbs.jpg"}).encode(), {})
            if kwargs["method"] == "HEAD" and "res.cloudinary.com" in kwargs["url"]:
                return HTTPResponse(200, b"", {"content-type": "image/jpeg"})
            return HTTPResponse(404, b"", {})

        cfg_cloud = AppConfig(
            image_host_provider="cloudinary",
            cloudinary_cloud_name="demo",
            cloudinary_upload_preset="unsigned_blog",
        )
        uploader_cloud = ImageUploader(cfg_cloud, http_client=ResilientHTTPClient(transport=transport, max_retries=0))
        hosted = uploader_cloud.upload(asset)
        self.assertEqual(hosted, "https://res.cloudinary.com/demo/herbs.jpg")
        self.assertEqual(asset.hosted_url, hosted)


if __name__ == "__main__":
    unittest.main()
