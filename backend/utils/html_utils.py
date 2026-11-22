"""HTML validation, sanitization, slug generation, and readability helpers."""

from __future__ import annotations

import html
import re
from bs4 import BeautifulSoup


DISALLOWED_TAGS = {"script", "style", "iframe", "object", "embed", "form", "input"}


def slugify(text: str, max_length: int = 70) -> str:
    """Generate a clean SEO-friendly URL slug."""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
    cleaned = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit("-", 1)[0]
    return cleaned or "article"


def sanitize_blogger_html(raw_html: str) -> str:
    """Remove unsafe tags and inline event handlers while preserving valid Blogger HTML."""
    soup = BeautifulSoup(raw_html or "", "html.parser")
    for tag in soup.find_all(list(DISALLOWED_TAGS)):
        tag.decompose()
    for tag in soup.find_all(True):
        attrs_to_remove = [a for a in tag.attrs if a.lower().startswith("on")]
        for attr in attrs_to_remove:
            del tag.attrs[attr]
        if tag.name == "a" and "href" in tag.attrs:
            href = str(tag.attrs["href"]).strip()
            if href.lower().startswith("javascript:"):
                del tag.attrs["href"]
    return str(soup).strip()


def validate_article_html(raw_html: str) -> list[str]:
    """Validate generated article HTML structure and return a list of issues."""
    issues: list[str] = []
    if not raw_html or not raw_html.strip():
        return ["Article HTML content is empty."]

    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count < 150:
        issues.append(f"Article body is too short ({word_count} words; minimum recommended is 150).")

    h2_tags = soup.find_all("h2")
    if len(h2_tags) < 2:
        issues.append("Article should contain at least 2 H2 section headings.")

    h1_tags = soup.find_all("h1")
    if h1_tags:
        issues.append("Avoid H1 tags inside Blogger post body; Blogger renders the post title as H1.")

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    if len(paragraphs) < 3:
        issues.append("Article should contain at least 3 body paragraphs (intro, body, conclusion).")

    for img in soup.find_all("img"):
        if not img.get("src"):
            issues.append("Found an <img> tag missing its src attribute.")
        if not img.get("alt") or not str(img.get("alt")).strip():
            issues.append("Found an <img> tag missing descriptive alt text.")

    return issues


def strip_html_to_text(raw_html: str) -> str:
    """Extract clean plain text from HTML."""
    soup = BeautifulSoup(raw_html or "", "html.parser")
    return html.unescape(soup.get_text(" ", strip=True))


def estimate_flesch_kincaid_grade(text: str) -> float:
    """Compute Flesch-Kincaid Grade Level for readability diagnostics."""
    words = re.findall(r"[A-Za-z]+", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if not words or not sentences:
        return 0.0

    def _syllables(word: str) -> int:
        w = word.lower()
        w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
        w = re.sub(r"^y", "", w)
        groups = re.findall(r"[aeiouy]{1,2}", w)
        return max(1, len(groups))

    total_syllables = sum(_syllables(w) for w in words)
    grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (total_syllables / len(words)) - 15.59
    return round(max(0.0, grade), 2)
