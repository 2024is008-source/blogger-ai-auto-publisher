"""Unit tests for Gemini client and 10-step article generation workflow."""

from __future__ import annotations

import json
import unittest

from backend.ai.article_generator import ArticleGenerator
from backend.ai.gemini_client import GeminiClient
from backend.models.schemas import ArticleGenerationRequest, ArticleStatus, ArticleTemplate
from backend.utils.errors import GeminiAPIError, GeminiQuotaError
from backend.utils.http_client import HTTPResponse, ResilientHTTPClient


def _gemini_ok_response(text: str) -> HTTPResponse:
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode("utf-8")
    return HTTPResponse(status_code=200, body=body, headers={"content-type": "application/json"})


class TestArticleGenerator(unittest.TestCase):
    def test_ten_step_article_generation_success(self) -> None:
        responses = [
            _gemini_ok_response(
                json.dumps(
                    {
                        "suggested_titles": [
                            "Indoor Herb Gardening for Beginners: Complete Practical Guide",
                            "How to Grow Fresh Kitchen Herbs Indoors",
                        ],
                        "outline": ["Choosing the Right Herbs", "Light and Watering Basics", "Conclusion"],
                    }
                )
            ),
            _gemini_ok_response(
                "<p>Indoor herb gardening lets beginners grow fresh culinary herbs year-round with minimal space.</p>"
                "<h2>Choosing the Right Herbs</h2>"
                "<p>Basil, mint, parsley, and chives adapt well to sunny windowsills and compact containers.</p>"
                "<h2>Light and Watering Basics</h2>"
                "<p>Provide six hours of bright light daily and use well-draining potting mix to avoid root rot.</p>"
                "<script>alert('xss')</script>"
                "<h2>Conclusion</h2>"
                "<p>Start with two hardy varieties and expand your indoor herb garden as you build confidence.</p>"
            ),
            _gemini_ok_response(
                json.dumps(
                    {
                        "meta_description": "Learn practical indoor herb gardening tips for beginners, including light, soil, and easy starter plants.",
                        "slug": "indoor-herb-gardening-beginners-guide",
                        "labels": ["Gardening", "Indoor Herbs", "Home"],
                        "image_keywords": ["indoor kitchen herbs windowsill", "potted fresh basil"],
                        "image_alt_texts": ["Potted culinary herbs on a bright windowsill", "Fresh basil leaves in terracotta pot"],
                    }
                )
            ),
        ]
        idx = {"n": 0}

        def transport(**kwargs):
            self.assertIn("gemini-2.5-flash:generateContent", kwargs["url"])
            resp = responses[idx["n"]]
            idx["n"] += 1
            return resp

        http = ResilientHTTPClient(transport=transport, max_retries=0)
        gemini = GeminiClient("test-api-key", model="gemini-2.5-flash", http_client=http)
        generator = ArticleGenerator(gemini)

        req = ArticleGenerationRequest(
            main_keyword="indoor herb gardening",
            secondary_keywords=["basil care", "windowsill herbs"],
            template=ArticleTemplate.BEGINNER_GUIDE.value,
            num_sections=3,
            num_images=2,
        )
        article = generator.generate(req)

        self.assertEqual(article.status, ArticleStatus.GENERATED.value)
        self.assertIn("Indoor Herb Gardening", article.title)
        self.assertEqual(article.slug, "indoor-herb-gardening-beginners-guide")
        self.assertNotIn("<script>", article.html_content)
        self.assertEqual(len(article.outline), 3)
        self.assertEqual(len(article.image_keywords), 2)
        self.assertEqual(len(article.image_alt_texts), 2)

    def test_gemini_quota_and_invalid_key_errors(self) -> None:
        http_429 = ResilientHTTPClient(
            transport=lambda **_: HTTPResponse(429, b'{"error":"RESOURCE_EXHAUSTED"}', {}),
            max_retries=0,
        )
        client_429 = GeminiClient("fake-key", http_client=http_429)
        with self.assertRaises(GeminiQuotaError):
            client_429.generate_text("test prompt")

        http_401 = ResilientHTTPClient(
            transport=lambda **_: HTTPResponse(401, b'{"error":"API key not valid"}', {}),
            max_retries=0,
        )
        client_401 = GeminiClient("bad-key", http_client=http_401)
        with self.assertRaises(GeminiAPIError) as ctx:
            client_401.generate_text("test prompt")
        self.assertEqual(ctx.exception.code, "GEMINI_INVALID_KEY")

    def test_regenerate_paragraph(self) -> None:
        http = ResilientHTTPClient(
            transport=lambda **_: _gemini_ok_response("<p>Improved, concise explanation of windowsill light.</p>"),
            max_retries=0,
        )
        generator = ArticleGenerator(GeminiClient("test-key", http_client=http))
        from backend.models.schemas import Article

        art = Article(title="Herb Guide", main_keyword="herbs")
        rewritten = generator.regenerate_paragraph(art, "<p>Old text.</p>")
        self.assertIn("Improved, concise explanation", rewritten)


if __name__ == "__main__":
    unittest.main()
