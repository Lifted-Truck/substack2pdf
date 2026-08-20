#!/usr/bin/env python3
"""
guardian2pdf — Convert Guardian articles to clean, formatted PDFs.

A sibling of substack2pdf for theguardian.com. Guardian articles are free to
read, so no cookies are involved: give it a URL (or a saved HTML file) and it
writes a PDF with the headline, standfirst, byline, full body, and inline
images at their master resolution.

Usage:
    python guardian2pdf.py https://www.theguardian.com/news/2026/aug/18/some-article
    python guardian2pdf.py saved_page.html -o article.pdf

The rendering half of the pipeline (image embedding, CSS, HTML assembly, PDF
render, the macOS native-library fix) is REUSED from substack2pdf rather than
copied — only fetch/extract/clean differ per publication. This is the smallest
honest step toward the adapter registry in ROADMAP Phase 3: two publications
sharing one renderer, without yet paying for the full abstraction.

Dependencies: pip install requests beautifulsoup4 lxml weasyprint
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

# Shared machinery. substack2pdf is import-safe (its work happens under main()).
from substack2pdf import (
    _ensure_native_libs,
    build_html,
    clean_source_url,
    embed_images,
    http_get,
    make_session,
    slugify,
    source_output_dir,
)

# Guardian article bodies are far cleaner than Substack's, so this list is
# short: promos and embeds that carry no article text.
STRIP_SELECTORS = [
    '[data-component="youtube-embed"]',
    '[data-component="rich-link"]',
    '[data-spacefinder-role="richLink"]',
    ".ad-slot",
    "gu-island[name='NewsletterSignupForm']",
    '[data-component="newsletter-signup"]',
    "figure.element-atom",          # interactive atoms don't render in print
    "figure.element-interactive",
]


def fetch_html(source: str, session: requests.Session) -> tuple[str, str]:
    """Return (html, base_url). Source may be a URL or a local file path."""
    if re.match(r"^https?://", source):
        resp = http_get(session, source)
        return resp.text, source
    path = Path(source)
    if not path.exists():
        sys.exit(f"error: {source} is neither a URL nor an existing file")
    html = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html)
    return html, (m.group(1) if m else "https://www.theguardian.com/")


def extract_metadata(soup: BeautifulSoup) -> dict:
    meta = {"title": "", "subtitle": "", "author": "", "publication": "", "date": ""}

    def og(prop):
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else ""

    meta["title"] = og("og:title") or (soup.h1.get_text(strip=True) if soup.h1 else "Untitled")
    # og:site_name is lowercase "the Guardian"; title-case it for the byline.
    meta["publication"] = og("og:site_name").replace("the Guardian", "The Guardian")

    # The standfirst is the Guardian's subtitle. It can carry links/markup.
    stand = soup.select_one('[data-gu-name="standfirst"]')
    if stand:
        meta["subtitle"] = " ".join(stand.get_text(" ", strip=True).split())
    elif og("og:description"):
        meta["subtitle"] = og("og:description")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in (data if isinstance(data, list) else [data]):
            if not isinstance(item, dict):
                continue
            if item.get("@type") in ("NewsArticle", "Article", "ReportageNewsArticle", "BlogPosting"):
                authors = item.get("author") or []
                if isinstance(authors, dict):
                    authors = [authors]
                names = [a.get("name", "") for a in authors if isinstance(a, dict)]
                if names and not meta["author"]:
                    meta["author"] = ", ".join(n for n in names if n)
                if item.get("datePublished") and not meta["date"]:
                    meta["date"] = _fmt_date(item["datePublished"])

    if not meta["author"]:
        byline = soup.select_one('[data-gu-name="byline"]')
        if byline:
            meta["author"] = byline.get_text(" ", strip=True)

    if not meta["date"]:
        t = soup.find("meta", property="article:published_time")
        if t and t.get("content"):
            meta["date"] = _fmt_date(t["content"])

    return meta


def _fmt_date(raw: str) -> str:
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%B %-d, %Y")
    except ValueError:
        return raw[:10]


def find_body(soup: BeautifulSoup) -> Tag:
    for sel in ('[data-gu-name="body"]', ".article-body-commercial-selector",
                "#maincontent", "article"):
        body = soup.select_one(sel)
        if body is not None:
            return body
    sys.exit("error: could not locate the article body — is this a Guardian article page?")


def clean_body(body: Tag) -> None:
    for selector in STRIP_SELECTORS:
        for el in body.select(selector):
            el.decompose()
    for el in body.find_all(["script", "style", "noscript", "button", "svg", "form"]):
        el.decompose()
    # Newsletter/promo asides carry no article text. Identified by role rather
    # than by class: Guardian class names are hashed (e.g. dcr-11zfjs0) and
    # change between deploys, so matching them would rot on the next release.
    for el in body.find_all("aside"):
        el.decompose()
    # Unwrap link-wrapped images so the <img> renders directly.
    for a in body.find_all("a"):
        if a.find("img") and not a.get_text(strip=True):
            a.unwrap()
    for p in body.find_all(["p", "div"]):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()
    _strip_trailing_chrome(body)


def _content_container(body: Tag) -> Tag:
    """Descend through single-element wrapper divs to the block holding the prose."""
    node = body
    while True:
        kids = [c for c in node.children if isinstance(c, Tag)]
        if len(kids) == 1 and kids[0].name in ("div", "article", "section"):
            node = kids[0]
        else:
            return node


# Prose-bearing tags: a trailing block containing none of these is site chrome.
# `li` is deliberately NOT here — the Guardian's closing tag list is a <ul> of
# links, so counting <li> as prose kept exactly the block we mean to drop. A
# genuine trailing list is caught instead by the link-ratio test below.
_PROSE = ("p", "img", "figure", "blockquote", "h1", "h2", "h3", "h4")

# A block whose visible text is mostly link text is navigation, not prose.
_LINK_TEXT_CHROME_RATIO = 0.6


def _strip_trailing_chrome(body: Tag) -> None:
    """Drop trailing blocks that carry no prose — the Guardian closes an article
    with a tag list and a share/"Reuse this content" bar, which otherwise land in
    the PDF as a run of stray link text. Detected structurally (no <p>/<img>
    inside) rather than by class name: Guardian class names are hashed (dcr-…)
    and change between deploys, so a class match would silently rot."""
    container = _content_container(body)
    while True:
        kids = [c for c in container.children if isinstance(c, Tag)]
        if not kids:
            return
        last = kids[-1]
        if last.name in _PROSE or last.find(list(_PROSE)) is not None:
            return
        text = last.get_text(strip=True)
        if text:
            link_text = "".join(a.get_text(strip=True) for a in last.find_all("a"))
            if len(link_text) < _LINK_TEXT_CHROME_RATIO * len(text):
                return          # mostly non-link text: real content, keep it
        last.decompose()


def main():
    ap = argparse.ArgumentParser(description="Convert a Guardian article to a formatted PDF.")
    ap.add_argument("source", help="Article URL, or path to a saved HTML file")
    ap.add_argument("-o", "--output", help="Output PDF path (default: output/guardian/<title-slug>.pdf)")
    ap.add_argument("--source-url", action=argparse.BooleanOptionalAction, default=True,
                    help="Append the article's source URL to the end of the PDF (default: enabled)")
    args = ap.parse_args()

    session = make_session(None)     # Guardian articles are free — no cookies

    print(f"→ loading {args.source}")
    raw_html, base_url = fetch_html(args.source, session)
    soup = BeautifulSoup(raw_html, "lxml")

    meta = extract_metadata(soup)
    print(f"→ found: “{meta['title']}” by {meta['author'] or 'unknown'} ({meta['date'] or 'no date'})")

    body = find_body(soup)
    clean_body(body)

    with tempfile.TemporaryDirectory() as tmpdir:
        n_images = embed_images(body, base_url, session, tmpdir)
        print(f"→ embedded {n_images} image(s)")

        display_url = ""
        if args.source_url:
            if re.match(r"^https?://", args.source):
                display_url = clean_source_url(args.source)
            elif base_url and base_url != "https://www.theguardian.com/":
                display_url = base_url

        # No footnotes: the Guardian doesn't use Substack-style numbered notes.
        final_html = build_html(meta, body, [], source_url=display_url)

        out = args.output or os.path.join(source_output_dir("guardian"),
                                          f"{slugify(meta['title'])}.pdf")
        out_parent = os.path.dirname(out)
        if out_parent:
            os.makedirs(out_parent, exist_ok=True)
        print("→ rendering PDF…")
        _ensure_native_libs()
        from weasyprint import HTML
        HTML(string=final_html, base_url=tmpdir).write_pdf(out)
        print(f"✓ wrote {out}")


if __name__ == "__main__":
    main()
