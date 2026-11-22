import type { AppSettings, Article, SEOAnalysisResult, SEOCheck } from '../types';

export function analyzeArticleSEO(
  article: Article,
  settings: AppSettings,
  existingTitles: string[] = []
): SEOAnalysisResult {
  const checks: SEOCheck[] = [];
  const doc = new DOMParser().parseFromString(article.html_content || '', 'text/html');
  const plainText = (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
  const words = plainText ? plainText.match(/\b\w+\b/g) || [] : [];
  const wordCount = words.length;
  const kw = article.main_keyword.trim().toLowerCase();

  // 1. Title length
  const tLen = article.title.trim().length;
  if (tLen >= settings.seo_title_min && tLen <= settings.seo_title_max) {
    checks.push({ check: 'Title Length', status: 'pass', message: `${tLen} characters (within target).`, recommendation: '' });
  } else {
    checks.push({
      check: 'Title Length',
      status: 'warning',
      message: `${tLen} characters (target: ${settings.seo_title_min}-${settings.seo_title_max}).`,
      recommendation: `Adjust title length between ${settings.seo_title_min} and ${settings.seo_title_max} characters.`,
    });
  }

  // 2. Meta description
  const mLen = article.meta_description.trim().length;
  if (mLen >= settings.seo_meta_min && mLen <= settings.seo_meta_max) {
    checks.push({ check: 'Meta Description', status: 'pass', message: `${mLen} characters.`, recommendation: '' });
  } else if (mLen === 0) {
    checks.push({
      check: 'Meta Description',
      status: 'fail',
      message: 'Meta description is missing.',
      recommendation: `Write a concise summary (${settings.seo_meta_min}-${settings.seo_meta_max} chars).`,
    });
  } else {
    checks.push({
      check: 'Meta Description',
      status: 'warning',
      message: `${mLen} characters (target: ${settings.seo_meta_min}-${settings.seo_meta_max}).`,
      recommendation: `Refine description to ${settings.seo_meta_min}-${settings.seo_meta_max} characters.`,
    });
  }

  // 3. Keyword placement
  const firstP = doc.querySelector('p')?.textContent?.toLowerCase() || '';
  const inTitle = Boolean(kw && article.title.toLowerCase().includes(kw));
  const inIntro = Boolean(kw && firstP.includes(kw));
  if (inTitle && inIntro) {
    checks.push({ check: 'Keyword Placement', status: 'pass', message: 'Main keyword present in title and intro.', recommendation: '' });
  } else {
    checks.push({
      check: 'Keyword Placement',
      status: 'warning',
      message: 'Main keyword missing in title or opening paragraph.',
      recommendation: 'Place the primary keyword naturally in both title and introduction.',
    });
  }

  // 4. Headings
  const h1 = doc.querySelectorAll('h1').length;
  const h2 = doc.querySelectorAll('h2').length;
  const h3 = doc.querySelectorAll('h3').length;
  if (h1 > 0) {
    checks.push({
      check: 'Heading Hierarchy',
      status: 'warning',
      message: `Found ${h1} H1 tag(s) in body.`,
      recommendation: 'Use H2/H3 in body; Blogger renders the post title as H1.',
    });
  } else if (h2 >= 2) {
    checks.push({ check: 'Heading Hierarchy', status: 'pass', message: `${h2} H2 and ${h3} H3 headings.`, recommendation: '' });
  } else {
    checks.push({
      check: 'Heading Hierarchy',
      status: 'fail',
      message: `Only ${h2} H2 heading(s) found.`,
      recommendation: 'Add descriptive H2 headings for each major section.',
    });
  }

  // 5 & 6. Links
  const links = Array.from(doc.querySelectorAll('a[href]'));
  const externalLinks = links.filter((a) => /^https?:\/\//i.test(a.getAttribute('href') || '')).length;
  const internalLinks = links.length - externalLinks;
  checks.push({
    check: 'Internal Links',
    status: internalLinks > 0 ? 'pass' : 'warning',
    message: `${internalLinks} internal link(s).`,
    recommendation: internalLinks > 0 ? '' : 'Link to 1-3 related posts on your blog.',
  });
  checks.push({
    check: 'External Links',
    status: externalLinks > 0 ? 'pass' : 'warning',
    message: `${externalLinks} external link(s).`,
    recommendation: externalLinks > 0 ? '' : 'Cite authoritative external sources where relevant.',
  });

  // 7 & 8. Images & Alt Text
  const imgs = Array.from(doc.querySelectorAll('img'));
  const missingAlt = imgs.filter((img) => !(img.getAttribute('alt') || '').trim()).length;
  checks.push({
    check: 'Image Availability',
    status: imgs.length > 0 ? 'pass' : 'warning',
    message: `${imgs.length} embedded image(s).`,
    recommendation: imgs.length > 0 ? '' : 'Insert at least one copyright-permitted image.',
  });
  checks.push({
    check: 'Image Alt Text',
    status: imgs.length > 0 && missingAlt === 0 ? 'pass' : missingAlt > 0 ? 'fail' : 'warning',
    message: missingAlt > 0 ? `${missingAlt} image(s) missing alt text.` : imgs.length > 0 ? 'All images have alt text.' : 'No images to check.',
    recommendation: missingAlt > 0 ? 'Add descriptive alt attributes to all images.' : '',
  });

  // 9. Slug quality
  const slugOk = /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(article.slug.trim()) && article.slug.length <= 70;
  checks.push({
    check: 'Slug Quality',
    status: slugOk ? 'pass' : 'warning',
    message: slugOk ? `Clean slug: /${article.slug}` : 'Slug should be lowercase hyphenated words.',
    recommendation: slugOk ? '' : 'Use concise lowercase words separated by hyphens.',
  });

  // 10. Readability
  const sentences = plainText.split(/[.!?]+/).filter((s) => s.trim()).length || 1;
  const avgWordsPerSentence = wordCount / sentences;
  const grade = Number(Math.max(0, 0.39 * avgWordsPerSentence + 4.5).toFixed(1));
  checks.push({
    check: 'Readability',
    status: wordCount === 0 ? 'fail' : grade <= 12 ? 'pass' : 'warning',
    message: wordCount === 0 ? 'No body prose yet.' : `${wordCount} words (est. grade ${grade}).`,
    recommendation: grade > 12 ? 'Break up long sentences for easier reading.' : '',
  });

  // 11. Duplicate titles
  const dup = existingTitles.some((t) => t.trim().toLowerCase() === article.title.trim().toLowerCase());
  checks.push({
    check: 'Duplicate Titles',
    status: dup ? 'fail' : 'pass',
    message: dup ? 'Another article already uses this title.' : 'Title is unique.',
    recommendation: dup ? 'Differentiate the title before publishing.' : '',
  });

  // 12. Intro & Conclusion
  const paras = Array.from(doc.querySelectorAll('p')).filter((p) => (p.textContent || '').trim().length > 0);
  const hasSections = paras.length >= 3;
  checks.push({
    check: 'Section Completeness',
    status: hasSections ? 'pass' : 'warning',
    message: hasSections ? 'Introduction, body, and conclusion present.' : 'Fewer than 3 paragraphs.',
    recommendation: hasSections ? '' : 'Ensure an introduction, detailed sections, and conclusion.',
  });

  const pts = checks.reduce((acc, c) => acc + (c.status === 'pass' ? 1 : c.status === 'warning' ? 0.5 : 0), 0);
  const score = Math.round((pts / checks.length) * 100);

  return {
    score,
    checks,
    word_count: wordCount,
    readability_grade: grade,
    heading_counts: { h1, h2, h3 },
    internal_link_count: internalLinks,
    external_link_count: externalLinks,
    disclaimer: 'SEO checks evaluate structural on-page practices only; a high score does not guarantee search engine rankings.',
  };
}
