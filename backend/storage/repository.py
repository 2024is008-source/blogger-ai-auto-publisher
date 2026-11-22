"""File-based GitHub repository storage for non-sensitive application state."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from backend.models.schemas import (
    Article,
    BlogAccount,
    ImageAsset,
    PublishingHistoryRecord,
    QueueItem,
    ScheduleConfig,
    utc_now_iso,
)
from backend.utils.errors import StorageError


class RepositoryStorage:
    """Manages persistent JSON files inside the repository's `data/` directory."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.articles_dir = self.data_dir / "articles"
        self.history_dir = self.data_dir / "publishing-history"
        self.licenses_dir = self.data_dir / "image-licenses"

        self.queue_file = self.data_dir / "queue.json"
        self.blogs_file = self.data_dir / "blogs.json"
        self.history_file = self.history_dir / "history.json"
        self.licenses_file = self.licenses_dir / "licenses.json"
        self.schedule_file = self.data_dir / "schedule-config.json"
        self.settings_file = self.data_dir / "settings.json"
        self.logs_file = self.data_dir / "logs.json"

        self.ensure_layout()

    def ensure_layout(self) -> None:
        try:
            self.articles_dir.mkdir(parents=True, exist_ok=True)
            self.history_dir.mkdir(parents=True, exist_ok=True)
            self.licenses_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Unable to initialize data directory {self.data_dir}: {exc}") from exc

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            raw = path.read_text(encoding="utf-8").strip()
            return json.loads(raw) if raw else default
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed reading JSON file {path}: {exc}") from exc

    def _write_json(self, path: Path, payload: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed writing JSON file {path}: {exc}") from exc

    # --- Articles ---
    def save_article(self, article: Article) -> Path:
        article.updated_at = utc_now_iso()
        target = self.articles_dir / f"{article.id}.json"
        self._write_json(target, article.to_dict())
        return target

    def get_article(self, article_id: str) -> Article | None:
        target = self.articles_dir / f"{article_id}.json"
        if not target.exists():
            return None
        return Article.from_dict(self._read_json(target, {}))

    def list_articles(self) -> list[Article]:
        articles: list[Article] = []
        for path in sorted(self.articles_dir.glob("*.json")):
            data = self._read_json(path, {})
            if isinstance(data, dict) and data.get("id"):
                articles.append(Article.from_dict(data))
        articles.sort(key=lambda a: a.created_at, reverse=True)
        return articles

    def delete_article(self, article_id: str) -> bool:
        target = self.articles_dir / f"{article_id}.json"
        if target.exists():
            target.unlink()
            return True
        return False

    # --- Blogs ---
    def list_blogs(self) -> list[BlogAccount]:
        raw = self._read_json(self.blogs_file, [])
        return [BlogAccount.from_dict(item) for item in raw if isinstance(item, dict)]

    def save_blogs(self, blogs: list[BlogAccount]) -> None:
        self._write_json(self.blogs_file, [b.to_dict() for b in blogs])

    def upsert_blog(self, blog: BlogAccount) -> None:
        blogs = self.list_blogs()
        by_id = {b.blog_id: b for b in blogs}
        by_id[blog.blog_id] = blog
        self.save_blogs(list(by_id.values()))

    def get_blog(self, blog_id: str) -> BlogAccount | None:
        for b in self.list_blogs():
            if b.blog_id == blog_id:
                return b
        return None

    # --- Queue ---
    def list_queue(self) -> list[QueueItem]:
        raw = self._read_json(self.queue_file, [])
        return [QueueItem.from_dict(item) for item in raw if isinstance(item, dict)]

    def save_queue(self, items: list[QueueItem]) -> None:
        self._write_json(self.queue_file, [i.to_dict() for i in items])

    # --- Publishing History ---
    def list_history(self) -> list[PublishingHistoryRecord]:
        raw = self._read_json(self.history_file, [])
        records = [PublishingHistoryRecord.from_dict(r) for r in raw if isinstance(r, dict)]
        records.sort(key=lambda r: r.timestamp_utc, reverse=True)
        return records

    def append_history(self, record: PublishingHistoryRecord) -> None:
        records = self.list_history()
        records.insert(0, record)
        self._write_json(self.history_file, [r.to_dict() for r in records])

    def export_history_csv(self, records: list[PublishingHistoryRecord] | None = None) -> str:
        items = records if records is not None else self.list_history()
        buf = io.StringIO()
        fieldnames = [
            "record_id",
            "article_id",
            "article_title",
            "blog_id",
            "blog_name",
            "status",
            "timestamp_utc",
            "blogger_post_id",
            "article_url",
            "image_sources",
            "publishing_mode",
            "main_keyword",
            "error_details",
        ]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in items:
            row = r.to_dict()
            row["image_sources"] = "; ".join(r.image_sources)
            writer.writerow(row)
        return buf.getvalue()

    def export_history_json(self, records: list[PublishingHistoryRecord] | None = None) -> str:
        items = records if records is not None else self.list_history()
        return json.dumps([r.to_dict() for r in items], indent=2, ensure_ascii=False)

    # --- Image Licenses ---
    def list_image_licenses(self) -> list[ImageAsset]:
        raw = self._read_json(self.licenses_file, [])
        return [ImageAsset.from_dict(item) for item in raw if isinstance(item, dict)]

    def record_image_licenses(self, assets: list[ImageAsset]) -> None:
        existing = self.list_image_licenses()
        by_key = {(a.source_provider, a.id): a for a in existing}
        for asset in assets:
            by_key[(asset.source_provider, asset.id)] = asset
        self._write_json(self.licenses_file, [a.to_dict() for a in by_key.values()])

    # --- Schedule & Settings ---
    def get_schedule_config(self) -> ScheduleConfig:
        raw = self._read_json(self.schedule_file, {})
        if not isinstance(raw, dict) or not raw:
            return ScheduleConfig()
        return ScheduleConfig.from_dict(raw)

    def save_schedule_config(self, config: ScheduleConfig) -> None:
        self._write_json(self.schedule_file, config.to_dict())

    def get_settings(self) -> dict[str, Any]:
        defaults = {
            "gemini_model": "gemini-2.5-flash",
            "seo_title_min": 45,
            "seo_title_max": 65,
            "seo_meta_min": 120,
            "seo_meta_max": 160,
            "default_license_filter": "commercial_permitted",
            "default_timezone": "UTC",
            "image_host_provider": "none",
        }
        stored = self._read_json(self.settings_file, {})
        if isinstance(stored, dict):
            defaults.update(stored)
        return defaults

    def save_settings(self, settings: dict[str, Any]) -> None:
        # Strip any accidental secret-like keys before persisting to public repo files
        blocked_substrings = ("secret", "token", "api_key", "password", "service_role")
        safe_settings = {
            k: v
            for k, v in settings.items()
            if not any(b in k.lower() for b in blocked_substrings)
        }
        self._write_json(self.settings_file, safe_settings)
