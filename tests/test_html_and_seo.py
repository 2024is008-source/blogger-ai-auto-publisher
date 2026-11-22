"""Tests for HTML validation and 12-check SEO analysis."""

from __future__ import annotations

import unittest

from backend.ai.seo_optimizer import SEOOptimizer
from backend.models.schemas import Article
from backend.utils.html_utils import sanitize_blogger_html, validate_article_html


class TestHTMLAndSEO(unittest.TestCase):
    def test_html_validation_flags_h1_and_missing_alt(self) -> None:
        raw = "<h1>Bad Heading</h1><p>Short body</p><img src='https://example.com/a.jpg' />"
        issues = validate_article_html(raw)
        joined = " ".join(issues).lower()
        self.assertIn("h1", joined)
        self.assertIn("alt text", joined)
        self.assertIn("short", joined)

    def test_sanitize_strips_script_and_onclick(self) -> None:
        dirty = '<p onclick="evil()">Hello</p><script>steal()</script><a href="javascript:alert(1)">Bad</a>'
        clean = sanitize_blogger_html(dirty)
        self.assertNotIn("script", clean)
        self.assertNotIn("onclick", clean)
        self.assertNotIn("javascript:", clean)

    def test_seo_analysis_checks_and_disclaimer(self) -> None:
        html = (
            "<p>Indoor herb gardening is a practical way for apartment residents to enjoy fresh basil, mint, and chives every week without needing a backyard garden.</p>"
            "<h2>Selecting Starter Herbs</h2>"
            "<p>Choose hardy plants and read our <a href='/soil-guide'>potting soil guide</a> alongside "
            "<a href='https://extension.umn.edu/'>university gardening resources</a>.</p>"
            "<figure><img src='https://cdn.example.com/herbs.jpg' alt='Fresh potted herbs on a sunny windowsill' /></figure>"
            "<h2>Conclusion</h2>"
            "<p>With consistent sunlight, proper drainage, and regular harvesting, your indoor herb gardening setup will stay productive across all seasons.</p>"
        )
        article = Article(
            title="Indoor Herb Gardening Guide for Small Sunny Apartments",
            slug="indoor-herb-gardening-small-apartments",
            meta_description="Discover practical indoor herb gardening steps for apartments, including starter plants, drainage tips, and daily light care.",
            main_keyword="indoor herb gardening",
            html_content=html,
        )
        optimizer = SEOOptimizer(title_min=45, title_max=65, meta_min=115, meta_max=160)
        result = optimizer.analyze(article, existing_titles=["Unrelated Post"])

        self.assertGreaterEqual(result.score, 85)
        self.assertEqual(len(result.checks), 12)
        self.assertIn("does not guarantee search engine rankings", result.disclaimer)

        # Duplicate title check must fail when matching existing title
        dup_result = optimizer.analyze(article, existing_titles=[article.title])
        dup_check = next(c for c in dup_result.checks if c.check == "duplicate_titles")
        self.assertEqual(dup_check.status, "fail")


if __name__ == "__main__":
    unittest.main()
