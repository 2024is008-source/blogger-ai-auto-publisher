"""Multi-step SEO article generation workflow powered by Google Gemini."""

from __future__ import annotations

from typing import Any

from backend.ai.gemini_client import GeminiClient
from backend.models.schemas import (
    Article,
    ArticleGenerationRequest,
    ArticleStatus,
    ArticleTemplate,
)
from backend.utils.html_utils import sanitize_blogger_html, slugify, validate_article_html
from backend.utils.logger import StructuredLogger


TEMPLATE_GUIDELINES: dict[str, str] = {
    ArticleTemplate.INFORMATIONAL_GUIDE.value: (
        "Comprehensive informational guide with clear definitions, structured H2/H3 sections, "
        "practical takeaways, and an FAQ or summary."
    ),
    ArticleTemplate.HOW_TO_TUTORIAL.value: (
        "Step-by-step tutorial with prerequisites, numbered actionable steps under H2/H3 headings, "
        "common mistakes to avoid, and a verification wrap-up."
    ),
    ArticleTemplate.LISTICLE.value: (
        "Well-curated numbered listicle where each item has a descriptive H2 heading, concrete utility, "
        "pros/considerations, and a concluding summary."
    ),
    ArticleTemplate.PRODUCT_COMPARISON.value: (
        "Balanced comparison guide with evaluation criteria, an HTML comparison table, "
        "use-case recommendations, and transparent caveats."
    ),
    ArticleTemplate.BEGINNER_GUIDE.value: (
        "Accessible beginner guide explaining core concepts in plain language, step-by-step getting started advice, "
        "and next steps."
    ),
    ArticleTemplate.NEWS_ARTICLE.value: (
        "Objective news explainer using inverted-pyramid structure: what happened, context, key implications, "
        "and what readers should watch next. Do not fabricate quotes or unverified statistics."
    ),
    ArticleTemplate.HOME_AND_LIFESTYLE.value: (
        "Practical home and lifestyle article with realistic tips, planning checklists, and budget-friendly suggestions."
    ),
}

LENGTH_WORD_TARGETS: dict[str, int] = {
    "short": 800,
    "medium": 1400,
    "long": 2200,
}

QUALITY_SYSTEM_PROMPT = (
    "You are a senior editorial writer and technical SEO strategist. "
    "Write original, genuinely helpful articles tailored for Google Blogger HTML. "
    "Strict editorial rules:\n"
    "1. Never stuff keywords or repeat filler paragraphs.\n"
    "2. Use descriptive <h2> and <h3> headings (never use <h1> inside the body).\n"
    "3. Always include an engaging introduction and a practical conclusion.\n"
    "4. Place keywords naturally where they help the reader.\n"
    "5. NEVER fabricate statistics, survey percentages, study citations, or fake quotes.\n"
    "6. Clearly distinguish factual explanations from practical suggestions or opinions.\n"
    "7. Avoid unsupported medical, financial, or legal advice; add a brief disclaimer if relevant.\n"
    "8. Output clean, semantic Blogger-compatible HTML (<p>, <h2>, <h3>, <ul>, <ol>, <li>, <table>, <blockquote>)."
)


class ArticleGenerator:
    """Executes the 10-step article generation and regeneration workflow."""

    def __init__(self, gemini: GeminiClient, logger: StructuredLogger | None = None) -> None:
        self.gemini = gemini
        self.logger = logger or StructuredLogger()

    def generate(self, req: ArticleGenerationRequest) -> Article:
        """Run all 10 steps of the article generation workflow."""
        if not req.main_keyword.strip():
            raise ValueError("main_keyword is required to generate an article.")

        template_guide = TEMPLATE_GUIDELINES.get(
            req.template, TEMPLATE_GUIDELINES[ArticleTemplate.INFORMATIONAL_GUIDE.value]
        )
        word_target = LENGTH_WORD_TARGETS.get(req.article_length.lower(), 1400)
        secondary_str = ", ".join(req.secondary_keywords) if req.secondary_keywords else "None specified"

        self.logger.info("article_generator", "Starting 10-step article generation", keyword=req.main_keyword)

        # Steps 2 & 3: Generate SEO-friendly titles and structured outline
        plan = self._generate_plan(req, template_guide, secondary_str)
        suggested_titles = [str(t).strip() for t in (plan.get("suggested_titles") or []) if str(t).strip()]
        chosen_title = req.article_title.strip() or (suggested_titles[0] if suggested_titles else req.main_keyword.title())
        outline = [str(h).strip() for h in (plan.get("outline") or []) if str(h).strip()]

        # Step 4: Generate full Blogger-compatible HTML article
        raw_html = self._generate_html_body(
            req=req,
            title=chosen_title,
            outline=outline,
            template_guide=template_guide,
            word_target=word_target,
            secondary_str=secondary_str,
        )
        clean_html = sanitize_blogger_html(raw_html)

        # Steps 5, 6, 7, 8, 9: Meta description, slug, labels, image search keywords, image alt text
        metadata = self._generate_metadata(req, chosen_title, outline)
        meta_description = str(metadata.get("meta_description") or "").strip()[:160]
        slug = slugify(str(metadata.get("slug") or chosen_title))
        labels = [str(lbl).strip() for lbl in (metadata.get("labels") or []) if str(lbl).strip()][:8]
        image_keywords = [
            str(kw).strip() for kw in (metadata.get("image_keywords") or [req.main_keyword]) if str(kw).strip()
        ][: max(1, req.num_images + 2)]
        image_alt_texts = [
            str(alt).strip() for alt in (metadata.get("image_alt_texts") or []) if str(alt).strip()
        ]
        while len(image_alt_texts) < max(1, req.num_images):
            image_alt_texts.append(f"Illustration related to {req.main_keyword}")

        # Step 10: Validate final article structure
        validation_issues = validate_article_html(clean_html)
        if validation_issues:
            self.logger.warning(
                "article_generator",
                "Article HTML validation reported issues",
                issues=validation_issues,
            )

        article = Article(
            title=chosen_title,
            suggested_titles=suggested_titles or [chosen_title],
            slug=slug,
            meta_description=meta_description,
            main_keyword=req.main_keyword.strip(),
            secondary_keywords=list(req.secondary_keywords),
            labels=labels or [req.main_keyword.strip().title()],
            outline=outline,
            html_content=clean_html,
            image_keywords=image_keywords,
            image_alt_texts=image_alt_texts,
            template=req.template,
            language=req.language,
            target_country=req.target_country,
            target_audience=req.target_audience,
            blog_id=req.blog_id,
            status=ArticleStatus.GENERATED.value,
        )
        self.logger.info("article_generator", "Article generated successfully", article_id=article.id, title=article.title)
        return article

    def regenerate_paragraph(self, article: Article, selected_paragraph: str, instruction: str = "") -> str:
        """Regenerate a specific selected paragraph while preserving article tone and HTML."""
        prompt = (
            f"Article title: {article.title}\n"
            f"Main keyword: {article.main_keyword}\n"
            f"Language: {article.language}\n"
            f"Rewrite the following HTML paragraph so it is clearer, original, and natural. "
            f"Avoid fabricated statistics. Return ONLY the rewritten <p>...</p> HTML.\n"
            f"Additional instruction: {instruction or 'Improve clarity and depth.'}\n\n"
            f"Original paragraph:\n{selected_paragraph}"
        )
        rewritten = self.gemini.generate_text(prompt, system_instruction=QUALITY_SYSTEM_PROMPT, temperature=0.65)
        return sanitize_blogger_html(rewritten)

    def _generate_plan(
        self, req: ArticleGenerationRequest, template_guide: str, secondary_str: str
    ) -> dict[str, Any]:
        prompt = (
            f"Create an SEO article plan in JSON with keys `suggested_titles` (array of 4 concise SEO titles, "
            f"45-65 characters each) and `outline` (array of {max(3, req.num_sections)} descriptive H2 section headings).\n"
            f"Main keyword: {req.main_keyword}\n"
            f"Preferred title (if any): {req.article_title or 'Generate best options'}\n"
            f"Secondary keywords: {secondary_str}\n"
            f"Target country: {req.target_country}\n"
            f"Target audience: {req.target_audience}\n"
            f"Language: {req.language}\n"
            f"Template: {req.template} — {template_guide}\n"
        )
        result = self.gemini.generate_json(prompt, system_instruction=QUALITY_SYSTEM_PROMPT)
        return result if isinstance(result, dict) else {}

    def _generate_html_body(
        self,
        *,
        req: ArticleGenerationRequest,
        title: str,
        outline: list[str],
        template_guide: str,
        word_target: int,
        secondary_str: str,
    ) -> str:
        outline_bullets = "\n".join(f"- {h}" for h in outline) if outline else "- Introduction\n- Key Concepts\n- Practical Steps\n- Conclusion"
        prompt = (
            f"Write a complete, publication-ready blog post in clean Blogger-compatible HTML.\n"
            f"Title (do NOT repeat as <h1>): {title}\n"
            f"Main keyword: {req.main_keyword}\n"
            f"Secondary keywords: {secondary_str}\n"
            f"Target country: {req.target_country}\n"
            f"Target audience: {req.target_audience}\n"
            f"Language: {req.language}\n"
            f"Writing style: {req.writing_style}\n"
            f"Target length: approximately {word_target} words\n"
            f"Template guidance: {template_guide}\n"
            f"Outline sections:\n{outline_bullets}\n\n"
            f"Requirements:\n"
            f"- Start with a strong introduction paragraph (<p>).\n"
            f"- Use <h2> for main sections and <h3> for subsections.\n"
            f"- Include helpful bulleted/numbered lists or an HTML <table> where genuinely useful.\n"
            f"- End with a practical conclusion section.\n"
            f"- Return ONLY the HTML body fragment (no <html>, <head>, <body>, or markdown code fences)."
        )
        raw = self.gemini.generate_text(prompt, system_instruction=QUALITY_SYSTEM_PROMPT, temperature=0.7)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def _generate_metadata(
        self, req: ArticleGenerationRequest, title: str, outline: list[str]
    ) -> dict[str, Any]:
        prompt = (
            f"Generate SEO and media metadata as JSON with keys:\n"
            f"- `meta_description`: compelling summary between 125 and 155 characters including the main keyword naturally\n"
            f"- `slug`: short lowercase hyphenated URL slug\n"
            f"- `labels`: array of 3 to 6 Blogger labels\n"
            f"- `image_keywords`: array of {max(2, req.num_images)} specific visual search queries for stock/CC photo search\n"
            f"- `image_alt_texts`: array of {max(2, req.num_images)} descriptive, accessible alt texts\n\n"
            f"Title: {title}\n"
            f"Main keyword: {req.main_keyword}\n"
            f"Language: {req.language}\n"
            f"Outline: {', '.join(outline)}\n"
        )
        result = self.gemini.generate_json(prompt, system_instruction=QUALITY_SYSTEM_PROMPT, temperature=0.4)
        return result if isinstance(result, dict) else {}
