"""Domain data models for Blogger AI Auto Publisher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ArticleStatus(str, Enum):
    GENERATED = "Generated"
    EDITING = "Editing"
    APPROVED = "Approved"
    DRAFT = "Draft"
    SCHEDULED = "Scheduled"
    PUBLISHING = "Publishing"
    PUBLISHED = "Published"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class PublishingMode(str, Enum):
    MANUAL = "manual"
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    AUTOMATIC = "automatic"


class LicenseFilter(str, Enum):
    CC0_PUBLIC_DOMAIN = "cc0_public_domain"
    COMMERCIAL_PERMITTED = "commercial_permitted"
    CC_WITH_ATTRIBUTION = "cc_with_attribution"
    ALL_SUPPORTED = "all_supported"


class ArticleTemplate(str, Enum):
    INFORMATIONAL_GUIDE = "informational_guide"
    HOW_TO_TUTORIAL = "how_to_tutorial"
    LISTICLE = "listicle"
    PRODUCT_COMPARISON = "product_comparison"
    BEGINNER_GUIDE = "beginner_guide"
    NEWS_ARTICLE = "news_article"
    HOME_AND_LIFESTYLE = "home_and_lifestyle"


@dataclass
class ArticleGenerationRequest:
    main_keyword: str
    article_title: str = ""
    secondary_keywords: list[str] = field(default_factory=list)
    target_country: str = "United States"
    target_audience: str = "General readers"
    language: str = "English"
    writing_style: str = "Informative and practical"
    article_length: str = "medium"  # short (~800w), medium (~1500w), long (~2500w)
    num_sections: int = 5
    num_images: int = 2
    blog_id: str = ""
    template: str = ArticleTemplate.INFORMATIONAL_GUIDE.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImageAsset:
    id: str
    title: str
    original_url: str
    preview_url: str
    creator_name: str
    source_provider: str
    license_name: str
    license_url: str
    attribution_required: bool
    attribution_text: str
    retrieval_date: str = field(default_factory=utc_now_iso)
    commercial_use_permitted: bool | None = None
    hosted_url: str = ""
    alt_text: str = ""
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageAsset":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SEORecommendation:
    check: str
    status: str  # pass | warning | fail
    message: str
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SEOAnalysisResult:
    score: int
    checks: list[SEORecommendation] = field(default_factory=list)
    word_count: int = 0
    readability_grade: float = 0.0
    heading_counts: dict[str, int] = field(default_factory=dict)
    internal_link_count: int = 0
    external_link_count: int = 0
    disclaimer: str = (
        "SEO checks evaluate structural and on-page best practices only; "
        "a high score does not guarantee search engine rankings."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "checks": [c.to_dict() for c in self.checks],
            "word_count": self.word_count,
            "readability_grade": self.readability_grade,
            "heading_counts": self.heading_counts,
            "internal_link_count": self.internal_link_count,
            "external_link_count": self.external_link_count,
            "disclaimer": self.disclaimer,
        }


@dataclass
class Article:
    id: str = field(default_factory=lambda: f"art_{uuid.uuid4().hex[:12]}")
    title: str = ""
    suggested_titles: list[str] = field(default_factory=list)
    slug: str = ""
    meta_description: str = ""
    main_keyword: str = ""
    secondary_keywords: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    outline: list[str] = field(default_factory=list)
    html_content: str = ""
    image_keywords: list[str] = field(default_factory=list)
    image_alt_texts: list[str] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)
    template: str = ArticleTemplate.INFORMATIONAL_GUIDE.value
    language: str = "English"
    target_country: str = "United States"
    target_audience: str = "General readers"
    blog_id: str = ""
    status: str = ArticleStatus.GENERATED.value
    seo_analysis: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["images"] = [img.to_dict() if isinstance(img, ImageAsset) else img for img in self.images]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Article":
        payload = dict(data)
        raw_imgs = payload.get("images") or []
        payload["images"] = [
            ImageAsset.from_dict(img) if isinstance(img, dict) else img for img in raw_imgs
        ]
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


@dataclass
class BlogAccount:
    blog_id: str
    name: str
    url: str
    description: str = ""
    locale: str = "en"
    default_labels: list[str] = field(default_factory=list)
    default_timezone: str = "UTC"
    max_daily_posts: int = 3
    active: bool = True
    last_synced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlogAccount":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class QueueItem:
    queue_id: str = field(default_factory=lambda: f"q_{uuid.uuid4().hex[:12]}")
    article_id: str = ""
    title: str = ""
    target_blog_id: str = ""
    target_blog_name: str = ""
    article_content_ref: str = ""
    publishing_mode: str = PublishingMode.MANUAL.value
    status: str = ArticleStatus.GENERATED.value
    created_at: str = field(default_factory=utc_now_iso)
    scheduled_at_utc: str | None = None
    timezone_name: str = "UTC"
    published_at_utc: str | None = None
    blogger_post_id: str | None = None
    post_url: str | None = None
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PublishingHistoryRecord:
    record_id: str = field(default_factory=lambda: f"pub_{uuid.uuid4().hex[:12]}")
    article_id: str = ""
    article_title: str = ""
    blog_id: str = ""
    blog_name: str = ""
    status: str = ArticleStatus.PUBLISHED.value
    timestamp_utc: str = field(default_factory=utc_now_iso)
    blogger_post_id: str = ""
    article_url: str = ""
    image_sources: list[str] = field(default_factory=list)
    publishing_mode: str = PublishingMode.MANUAL.value
    main_keyword: str = ""
    error_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublishingHistoryRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScheduleConfig:
    enabled: bool = False
    frequency: str = "daily"  # daily | weekly | custom
    days_of_week: list[str] = field(default_factory=lambda: ["Mon", "Wed", "Fri"])
    preferred_time_local: str = "09:00"
    timezone_name: str = "UTC"
    max_daily_posts: int = 2
    target_blog_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
