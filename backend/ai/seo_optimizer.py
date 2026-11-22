"""On-page SEO analysis module with configurable limits and actionable recommendations."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from backend.models.schemas import Article, SEOAnalysisResult, SEORecommendation
from backend.utils.html_utils import estimate_flesch_kincaid_grade, strip_html_to_text


class SEOOptimizer:
    """Evaluates on-page SEO best practices without making ranking guarantees."""

    def __init__(
        self,
        *,
        title_min: int = 45,
        title_max: int = 65,
        meta_min: int = 120,
        meta_max: int = 160,
    ) -> None:
        self.title_min = title_min
        self.title_max = title_max
        self.meta_min = meta_min
        self.meta_max = meta_max

    def analyze(
        self,
        article: Article,
        *,
        existing_titles: list[str] | None = None,
        blog_domain: str = "",
    ) -> SEOAnalysisResult:
        checks: list[SEORecommendation] = []
        soup = BeautifulSoup(article.html_content or "", "html.parser")
        plain_text = strip_html_to_text(article.html_content or "")
        words = re.findall(r"\b\w+\b", plain_text)
        word_count = len(words)
        kw = article.main_keyword.strip().lower()

        # 1. Title length
        t_len = len(article.title.strip())
        if self.title_min <= t_len <= self.title_max:
            checks.append(SEORecommendation("title_length", "pass", f"Title length is {t_len} characters."))
        else:
            checks.append(
                SEORecommendation(
                    "title_length",
                    "warning",
                    f"Title length is {t_len} characters (configured target: {self.title_min}-{self.title_max}).",
                    f"Adjust title to stay between {self.title_min} and {self.title_max} characters.",
                )
            )

        # 2. Meta description length
        m_len = len(article.meta_description.strip())
        if self.meta_min <= m_len <= self.meta_max:
            checks.append(SEORecommendation("meta_description", "pass", f"Meta description is {m_len} characters."))
        elif m_len == 0:
            checks.append(
                SEORecommendation(
                    "meta_description",
                    "fail",
                    "Meta description is missing.",
                    f"Add a concise summary between {self.meta_min} and {self.meta_max} characters.",
                )
            )
        else:
            checks.append(
                SEORecommendation(
                    "meta_description",
                    "warning",
                    f"Meta description is {m_len} characters (configured target: {self.meta_min}-{self.meta_max}).",
                    f"Tighten or expand meta description to {self.meta_min}-{self.meta_max} characters.",
                )
            )

        # 3. Main keyword placement
        first_para = soup.find("p")
        first_para_text = first_para.get_text(" ", strip=True).lower() if first_para else ""
        in_title = bool(kw and kw in article.title.lower())
        in_intro = bool(kw and kw in first_para_text)
        kw_occurrences = len(re.findall(re.escape(kw), plain_text.lower())) if kw else 0
        density = (kw_occurrences / word_count * 100) if word_count and kw else 0.0

        if not kw:
            checks.append(
                SEORecommendation("keyword_placement", "warning", "No main keyword specified.", "Set a primary keyword.")
            )
        elif density > 3.5:
            checks.append(
                SEORecommendation(
                    "keyword_placement",
                    "warning",
                    f"Keyword density is high ({density:.1f}%), which may read as keyword stuffing.",
                    "Replace repetitive keyword occurrences with natural synonyms.",
                )
            )
        elif in_title and in_intro:
            checks.append(
                SEORecommendation(
                    "keyword_placement",
                    "pass",
                    f"Main keyword appears naturally in title and introduction ({density:.1f}% density).",
                )
            )
        else:
            checks.append(
                SEORecommendation(
                    "keyword_placement",
                    "warning",
                    "Main keyword is missing from either the title or the opening paragraph.",
                    "Include the primary keyword naturally in both the title and introduction.",
                )
            )

        # 4. Heading hierarchy
        h1_count = len(soup.find_all("h1"))
        h2_count = len(soup.find_all("h2"))
        h3_count = len(soup.find_all("h3"))
        heading_counts = {"h1": h1_count, "h2": h2_count, "h3": h3_count}
        if h1_count > 0:
            checks.append(
                SEORecommendation(
                    "heading_hierarchy",
                    "warning",
                    f"Found {h1_count} H1 tag(s) inside body HTML.",
                    "Use H2 and H3 tags in body content; Blogger automatically renders the title as H1.",
                )
            )
        elif h2_count >= 2:
            checks.append(
                SEORecommendation("heading_hierarchy", "pass", f"Clear hierarchy with {h2_count} H2 and {h3_count} H3 headings.")
            )
        else:
            checks.append(
                SEORecommendation(
                    "heading_hierarchy",
                    "fail",
                    f"Only {h2_count} H2 heading(s) found.",
                    "Break the article into at least 2-4 descriptive H2 sections.",
                )
            )

        # 5 & 6. Internal and external links
        internal_links = 0
        external_links = 0
        parsed_blog_host = urlparse(blog_domain).netloc.lower() if blog_domain else ""
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if not href or href.startswith("#"):
                continue
            parsed = urlparse(href)
            if not parsed.netloc or (parsed_blog_host and parsed.netloc.lower() == parsed_blog_host):
                internal_links += 1
            else:
                external_links += 1

        if internal_links > 0:
            checks.append(SEORecommendation("internal_links", "pass", f"Contains {internal_links} internal link(s)."))
        else:
            checks.append(
                SEORecommendation(
                    "internal_links",
                    "warning",
                    "No internal links detected.",
                    "Link to 1-3 related posts on your Blogger site to aid reader navigation.",
                )
            )

        if external_links > 0:
            checks.append(SEORecommendation("external_links", "pass", f"Contains {external_links} external reference link(s)."))
        else:
            checks.append(
                SEORecommendation(
                    "external_links",
                    "warning",
                    "No external links detected.",
                    "Consider citing authoritative primary sources where helpful.",
                )
            )

        # 7 & 8. Image availability & alt text
        imgs = soup.find_all("img")
        if imgs or article.images:
            checks.append(
                SEORecommendation("image_availability", "pass", f"Article includes {max(len(imgs), len(article.images))} image(s).")
            )
        else:
            checks.append(
                SEORecommendation(
                    "image_availability",
                    "warning",
                    "No images embedded in article.",
                    "Use Image Finder to add at least one copyright-permitted image.",
                )
            )

        missing_alt = [img for img in imgs if not str(img.get("alt") or "").strip()]
        if imgs and not missing_alt:
            checks.append(SEORecommendation("image_alt_text", "pass", "All embedded images include descriptive alt text."))
        elif missing_alt:
            checks.append(
                SEORecommendation(
                    "image_alt_text",
                    "fail",
                    f"{len(missing_alt)} image(s) missing alt text.",
                    "Add concise, descriptive alt attributes to every <img> tag.",
                )
            )
        else:
            checks.append(
                SEORecommendation("image_alt_text", "warning", "No embedded <img> tags to evaluate alt text.")
            )

        # 9. Slug quality
        slug = article.slug.strip()
        if slug and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) and len(slug) <= 70:
            checks.append(SEORecommendation("slug_quality", "pass", f"Clean URL slug: '{slug}'."))
        else:
            checks.append(
                SEORecommendation(
                    "slug_quality",
                    "warning",
                    f"Slug '{slug or '(empty)'}' can be improved.",
                    "Use lowercase words separated by hyphens (under 70 characters).",
                )
            )

        # 10. Content readability
        grade = estimate_flesch_kincaid_grade(plain_text)
        if word_count == 0:
            checks.append(SEORecommendation("readability", "fail", "No readable body text found.", "Generate or write body content."))
        elif grade <= 12.0:
            checks.append(SEORecommendation("readability", "pass", f"Readable prose (estimated grade level {grade})."))
        else:
            checks.append(
                SEORecommendation(
                    "readability",
                    "warning",
                    f"Dense prose detected (estimated grade level {grade}).",
                    "Shorten long sentences and break dense paragraphs into scannable blocks.",
                )
            )

        # 11. Duplicate titles
        normalized_existing = {t.strip().lower() for t in (existing_titles or []) if t.strip()}
        if article.title.strip().lower() in normalized_existing:
            checks.append(
                SEORecommendation(
                    "duplicate_titles",
                    "fail",
                    "An existing article already uses this exact title.",
                    "Differentiate the title to avoid duplicate content and self-competition.",
                )
            )
        else:
            checks.append(SEORecommendation("duplicate_titles", "pass", "Title is unique among stored articles."))

        # 12. Missing sections (intro & conclusion)
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        has_intro = len(paragraphs) >= 1 and len(paragraphs[0].split()) >= 15
        has_conclusion = len(paragraphs) >= 3 and (
            any("conclusion" in h.get_text(" ", strip=True).lower() or "summary" in h.get_text(" ", strip=True).lower() or "final" in h.get_text(" ", strip=True).lower() for h in soup.find_all(["h2", "h3"]))
            or len(paragraphs[-1].split()) >= 15
        )
        if has_intro and has_conclusion:
            checks.append(SEORecommendation("missing_sections", "pass", "Includes clear introduction and concluding content."))
        else:
            checks.append(
                SEORecommendation(
                    "missing_sections",
                    "warning",
                    "Introduction or conclusion section appears incomplete.",
                    "Ensure the article opens with a clear introduction and closes with a helpful conclusion.",
                )
            )

        # Score calculation (transparent weighted rubric)
        points = 0.0
        for c in checks:
            if c.status == "pass":
                points += 1.0
            elif c.status == "warning":
                points += 0.5
        score = int(round((points / max(1, len(checks))) * 100))

        return SEOAnalysisResult(
            score=score,
            checks=checks,
            word_count=word_count,
            readability_grade=grade,
            heading_counts=heading_counts,
            internal_link_count=internal_links,
            external_link_count=external_links,
        )
