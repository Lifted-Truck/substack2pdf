#!/usr/bin/env python3
"""
substack2pdf — Convert Substack articles to clean, formatted PDFs.

Handles: title/subtitle/byline, full article body, inline images (downloaded
and embedded at high resolution), captions, pull quotes, code blocks, and
footnotes (rendered as a linked Notes section with backlinks).

Usage:
    # From a URL (works for free/public posts)
    python substack2pdf.py https://example.substack.com/p/some-post

    # From HTML saved out of your browser (works for paywalled posts:
    # Cmd+S / "Save Page As" while logged in, then point at the file)
    python substack2pdf.py saved_page.html

    # With browser cookies for paywalled posts directly from URL
    # (export cookies.txt with a browser extension like "Get cookies.txt")
    python substack2pdf.py https://... --cookies cookies.txt

    # PDFs go to ./output/substack/<publication>/ by default; override with -o
    python substack2pdf.py https://... -o article.pdf

Dependencies: pip install requests beautifulsoup4 lxml weasyprint
"""

import argparse
import base64
import html as html_mod
import io
import json
import mimetypes
import os
import re
import sys
import tempfile
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


def _ensure_native_libs() -> None:
    """WeasyPrint needs Pango/GLib/Cairo. On macOS these live under the
    Homebrew prefix, which the python.org framework Python does not search by
    default. Prepend it so the lazy `import weasyprint` can dlopen them."""
    if sys.platform != "darwin":
        return
    for prefix in ("/opt/homebrew", "/usr/local"):
        libdir = os.path.join(prefix, "lib")
        if os.path.isdir(libdir):
            existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            parts = [p for p in existing.split(os.pathsep) if p]
            if libdir not in parts:
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = os.pathsep.join([libdir, *parts])

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Default directory for generated PDFs (relative to this script, not the cwd)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Elements that are site chrome / engagement widgets, not article content
STRIP_SELECTORS = [
    ".subscription-widget", ".subscription-widget-wrap", ".subscribe-widget",
    ".subscription-widget-wrap-editor",
    ".button-wrapper", ".install-substack-app-embed",
    ".share-dialog", ".post-footer", ".publication-footer",
    ".digest-post-embed", ".community-chat-embed",
    ".poll-embed", ".audio-embed-container", ".video-embedded-container",
    "audio", "iframe[src*='substack.com/embed']",
    ".pencraft.frontend-components-AudioEmbedPlayer-module",
    ".embedded-post-wrap .post-cta",  # CTA inside embedded posts
]


# ---------------------------------------------------------------- fetching

def make_session(cookies_path: str | None) -> requests.Session:
    """Build a session with our UA and, optionally, browser cookies loaded."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    if cookies_path:
        jar = MozillaCookieJar(cookies_path)
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies = jar
    return session


def fetch_html(source: str, session: requests.Session) -> tuple[str, str]:
    """Return (html, base_url). Source may be a URL or a local file path."""
    if re.match(r"^https?://", source):
        resp = session.get(source, timeout=30)
        resp.raise_for_status()
        return resp.text, source
    path = Path(source)
    if not path.exists():
        sys.exit(f"error: {source} is neither a URL nor an existing file")
    html = path.read_text(encoding="utf-8", errors="replace")
    # try to recover canonical URL from the saved page for resolving relatives
    m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html)
    base = m.group(1) if m else "https://substack.com/"
    return html, base


# ---------------------------------------------------------------- parsing

def extract_metadata(soup: BeautifulSoup) -> dict:
    meta = {"title": "", "subtitle": "", "author": "", "publication": "", "date": ""}

    def og(prop):
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else ""

    meta["title"] = og("og:title") or (soup.h1.get_text(strip=True) if soup.h1 else "Untitled")
    meta["publication"] = og("og:site_name")

    sub = soup.select_one("h3.subtitle, .subtitle")
    if sub:
        meta["subtitle"] = sub.get_text(strip=True)
    elif og("og:description"):
        meta["subtitle"] = og("og:description")

    # JSON-LD usually has author + datePublished
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") in ("NewsArticle", "Article", "BlogPosting"):
                authors = item.get("author") or []
                if isinstance(authors, dict):
                    authors = [authors]
                names = [a.get("name", "") for a in authors if isinstance(a, dict)]
                meta["author"] = ", ".join(n for n in names if n)
                if item.get("datePublished"):
                    try:
                        dt = datetime.fromisoformat(item["datePublished"].replace("Z", "+00:00"))
                        meta["date"] = dt.strftime("%B %-d, %Y")
                    except ValueError:
                        meta["date"] = item["datePublished"][:10]

    if not meta["author"]:
        byline = soup.select_one(".byline-names, .post-header .pencraft a[href*='/@']")
        if byline:
            meta["author"] = byline.get_text(" ", strip=True)

    if not meta["date"]:
        t = soup.find("meta", property="article:published_time")
        if t and t.get("content"):
            try:
                dt = datetime.fromisoformat(t["content"].replace("Z", "+00:00"))
                meta["date"] = dt.strftime("%B %-d, %Y")
            except ValueError:
                meta["date"] = t["content"][:10]

    return meta


def find_body(soup: BeautifulSoup) -> Tag:
    body = soup.select_one("div.available-content div.body.markup")
    if body is None:
        body = soup.select_one("div.body.markup") or soup.select_one("div.available-content")
    if body is None:
        body = soup.find("article")
    if body is None:
        sys.exit("error: could not locate the article body — is this a Substack post page?")
    return body


def best_image_url(img: Tag, base_url: str) -> str | None:
    """Pick the highest-resolution source available for a Substack image."""
    candidates = []

    # srcset on the img or sibling <source> tags
    parents = [img]
    if img.parent and img.parent.name == "picture":
        parents += img.parent.find_all("source")
    for node in parents:
        srcset = node.get("srcset", "")
        for part in srcset.split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            url = bits[0]
            width = 0
            if len(bits) > 1 and bits[1].endswith("w"):
                try:
                    width = int(bits[1][:-1])
                except ValueError:
                    pass
            candidates.append((width, url))

    # the full-size original often hides in the enclosing <a class="image-link"> href
    parent_a = img.find_parent("a", class_=re.compile("image"))
    if parent_a and parent_a.get("href"):
        candidates.append((10_000, parent_a["href"]))

    if img.get("src"):
        candidates.append((1, img["src"]))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    url = candidates[0][1]
    # substack CDN URLs sometimes wrap the real URL: .../https%3A%2F%2F...
    if "substackcdn.com" in url or "substack-post-media" in url:
        m = re.search(r"/(https%3A%2F%2F.+)$", url)
        if m:
            url = unquote(m.group(1))
    if url.startswith("data:"):
        return url
    return urljoin(base_url, url)


def embed_images(body: Tag, base_url: str, session: requests.Session, tmpdir: str) -> int:
    """Download every image and rewrite src to a local file path. Returns count."""
    count = 0
    for img in body.find_all("img"):
        url = best_image_url(img, base_url)
        if not url:
            img.decompose()
            continue
        if url.startswith("data:"):
            continue  # already embedded
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "").split(";")[0]
            ext = mimetypes.guess_extension(ctype) or os.path.splitext(urlparse(url).path)[1] or ".jpg"
            if ext == ".jpe":
                ext = ".jpg"
            local = os.path.join(tmpdir, f"img_{count:03d}{ext}")
            with open(local, "wb") as fh:
                fh.write(resp.content)
            img.attrs = {"src": Path(local).as_uri(), "alt": img.get("alt", "")}
            count += 1
        except requests.RequestException:
            img.decompose()
    return count


def process_footnotes(soup: BeautifulSoup, body: Tag) -> list[dict]:
    """Collect footnotes, normalize in-text anchors, return ordered notes."""
    notes = []

    # In-text anchors: <a class="footnote-anchor" id="footnote-anchor-N">N</a>
    for anchor in body.select("a.footnote-anchor"):
        num = anchor.get_text(strip=True)
        anchor_id = anchor.get("id") or f"footnote-anchor-{num}"
        new = soup.new_tag("a", href=f"#fn-{num}", id=anchor_id)
        new["class"] = "fn-ref"
        sup = soup.new_tag("sup")
        sup.string = num
        new.append(sup)
        anchor.replace_with(new)

    # Footnote bodies: <div class="footnote"><a class="footnote-number">N</a>
    #                  <div class="footnote-content">...</div></div>
    for fn in soup.select("div.footnote"):
        num_tag = fn.select_one("a.footnote-number, .footnote-number")
        content = fn.select_one(".footnote-content")
        if not num_tag or not content:
            continue
        num = num_tag.get_text(strip=True)
        # unwrap paragraphs into inline-ish html
        inner = "".join(str(c) for c in content.contents).strip()
        notes.append({"num": num, "html": inner})
        fn.decompose()

    notes.sort(key=lambda n: int(n["num"]) if n["num"].isdigit() else 0)
    return notes


def clean_body(body: Tag) -> None:
    for selector in STRIP_SELECTORS:
        for el in body.select(selector):
            el.decompose()
    # strip event handlers / scripts / styles
    for el in body.find_all(["script", "style", "noscript", "button", "svg"]):
        el.decompose()
    # remove substack's image-link wrappers but keep the img
    for a in body.find_all("a", class_=re.compile("image-link")):
        a.unwrap() if a.find("img") else a.decompose()
    # drop empty paragraphs
    for p in body.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()
    # Substack appends decorative <hr> dividers just before the subscribe/CTA
    # widgets stripped above; once those widgets are gone the dividers are left
    # dangling at the end and render as stray "• • •" rules. Remove any trailing
    # dividers and empty wrappers (in-text dividers are kept — content follows).
    def _is_trailing_cruft(el: Tag) -> bool:
        if el.name == "hr":
            return True
        return not el.get_text(strip=True) and not el.find("img")

    while True:
        kids = [c for c in body.children if isinstance(c, Tag)]
        if kids and _is_trailing_cruft(kids[-1]):
            kids[-1].decompose()
        else:
            break


# ---------------------------------------------------------------- rendering

CSS = """
@page {
    size: letter;
    margin: 2.2cm 2.4cm 2.4cm 2.4cm;
    @bottom-center { content: counter(page); font-family: Georgia, serif;
                     font-size: 9pt; color: #888; }
}
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt;
       line-height: 1.55; color: #1a1a1a; }
header.article-header { margin-bottom: 1.6em; border-bottom: 1px solid #ddd;
                        padding-bottom: 1.1em; }
h1.title { font-size: 22pt; line-height: 1.2; margin: 0 0 0.35em 0;
           font-weight: 700; }
p.subtitle { font-size: 13pt; color: #555; margin: 0 0 0.9em 0;
             line-height: 1.35; font-style: italic; }
p.byline { font-size: 10pt; color: #666; margin: 0;
           text-transform: none; letter-spacing: 0.02em; }
p.byline .pub { font-weight: 600; color: #444; }
.body-content h1, .body-content h2 { font-size: 15.5pt; margin: 1.5em 0 0.5em; }
.body-content h3 { font-size: 13pt; margin: 1.4em 0 0.4em; }
.body-content h4 { font-size: 11.5pt; margin: 1.3em 0 0.35em; }
.body-content p { margin: 0 0 0.85em 0; }
.body-content a { color: #1a5276; text-decoration: none;
                  border-bottom: 0.5pt solid #aac4d4; }
a.fn-ref { border-bottom: none; color: #1a5276; font-weight: 600; }
.body-content blockquote { margin: 1em 0 1em 0; padding: 0.1em 0 0.1em 1.1em;
                           border-left: 2.5pt solid #c9c9c9; color: #444; }
.body-content .pullquote, .body-content .pull-quote {
    font-size: 14pt; font-style: italic; border: none; text-align: center; }
.body-content ul, .body-content ol { margin: 0 0 0.9em 0; padding-left: 1.6em; }
.body-content li { margin-bottom: 0.3em; }
.body-content hr { border: none; text-align: center; margin: 1.6em 0; }
.body-content hr::after { content: "•   •   •"; color: #999; font-size: 10pt; }
.body-content img { max-width: 100%; height: auto; display: block;
                    margin: 1.2em auto 0.4em auto; }
.body-content figure { margin: 1.2em 0; }
.body-content figcaption { font-size: 9pt; color: #777; text-align: center;
                           margin-top: 0.45em; line-height: 1.4; }
.body-content .captioned-image-container { margin: 1.2em 0; }
.body-content pre { background: #f6f6f4; border: 0.5pt solid #ddd;
                    padding: 0.7em 0.9em; font-size: 9pt; overflow-x: hidden;
                    white-space: pre-wrap; word-wrap: break-word;
                    font-family: 'DejaVu Sans Mono', Menlo, monospace; }
.body-content code { font-family: 'DejaVu Sans Mono', Menlo, monospace;
                     font-size: 9.5pt; background: #f4f4f2;
                     padding: 0.1em 0.25em; }
.body-content pre code { background: none; padding: 0; }
.body-content table { border-collapse: collapse; margin: 1em 0; font-size: 9.5pt; }
.body-content th, .body-content td { border: 0.5pt solid #ccc; padding: 0.35em 0.6em; }

section.footnotes { margin-top: 2.2em; border-top: 1px solid #ccc;
                    padding-top: 1em; }
section.footnotes h2 { font-size: 12pt; margin: 0 0 0.7em 0; }
.footnote-item { font-size: 9.5pt; line-height: 1.45; margin-bottom: 0.55em;
                 display: flex; }
.footnote-item .fn-num { min-width: 1.8em; font-weight: 700; color: #1a5276; }
.footnote-item .fn-body p { margin: 0 0 0.3em 0; }
.footnote-item .fn-body a { color: #1a5276; text-decoration: none; }

p.source-url { margin-top: 2.2em; padding-top: 0.9em; border-top: 1px solid #ddd;
               font-size: 9pt; color: #888; word-break: break-all; }
p.source-url .label { color: #666; font-weight: 600; }
p.source-url a { color: #1a5276; text-decoration: none; }
"""


def build_html(meta: dict, body: Tag, notes: list[dict], source_url: str = "") -> str:
    byline_bits = []
    if meta["author"]:
        byline_bits.append(html_mod.escape(meta["author"]))
    if meta["publication"]:
        byline_bits.append(f'<span class="pub">{html_mod.escape(meta["publication"])}</span>')
    if meta["date"]:
        byline_bits.append(html_mod.escape(meta["date"]))
    byline = " &nbsp;·&nbsp; ".join(byline_bits)

    notes_html = ""
    if notes:
        items = "\n".join(
            f'<div class="footnote-item" id="fn-{n["num"]}">'
            f'<span class="fn-num"><a href="#footnote-anchor-{n["num"]}">{n["num"]}.</a></span>'
            f'<span class="fn-body">{n["html"]}</span></div>'
            for n in notes
        )
        notes_html = f'<section class="footnotes"><h2>Notes</h2>\n{items}\n</section>'

    subtitle = f'<p class="subtitle">{html_mod.escape(meta["subtitle"])}</p>' if meta["subtitle"] else ""

    source_html = ""
    if source_url:
        esc = html_mod.escape(source_url)
        source_html = (
            f'<p class="source-url"><span class="label">Source:</span> '
            f'<a href="{esc}">{esc}</a></p>'
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<header class="article-header">
  <h1 class="title">{html_mod.escape(meta["title"])}</h1>
  {subtitle}
  <p class="byline">{byline}</p>
</header>
<div class="body-content">
{body.decode_contents()}
</div>
{notes_html}
{source_html}
</body></html>"""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:70] or "article"


def source_output_dir(platform: str, publication: str = "") -> str:
    """Directory for one source's PDFs: output/<platform>[/<publication>].

    Sources are kept apart so a mixed archive stays navigable — 100+ posts from
    one newsletter should not sit in the same flat folder as unrelated papers.
    """
    parts = [OUTPUT_DIR, slugify(platform)]
    if publication:
        parts.append(slugify(publication))
    return os.path.join(*parts)


def publication_slug(base_url: str, meta: dict) -> str:
    """Best-effort publication identifier for the output path.

    Substack publications are either `<name>.substack.com` or a custom domain,
    so the host is the reliable signal and og:site_name is the fallback (it is
    absent or generic often enough not to lead).
    """
    host = urlparse(base_url).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    if host.endswith(".substack.com"):
        return host[: -len(".substack.com")]
    # A bare substack.com (the saved-HTML fallback base) names no publication.
    if host and host != "substack.com":
        return host.split(".")[0]
    return slugify(meta.get("publication", "")) if meta.get("publication") else "unknown"


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Convert a Substack article to a formatted PDF.")
    ap.add_argument("source", help="Article URL, or path to an HTML file saved from your browser")
    ap.add_argument("-o", "--output",
                    help="Output PDF path (default: output/substack/<publication>/<title-slug>.pdf)")
    ap.add_argument("--cookies", help="Path to a Netscape-format cookies.txt (for paywalled posts)")
    ap.add_argument("--source-url", action=argparse.BooleanOptionalAction, default=True,
                    help="Append the article's source URL to the end of the PDF (default: enabled)")
    args = ap.parse_args()

    session = make_session(args.cookies)

    print(f"→ loading {args.source}")
    raw_html, base_url = fetch_html(args.source, session)
    soup = BeautifulSoup(raw_html, "lxml")

    meta = extract_metadata(soup)
    print(f"→ found: “{meta['title']}” by {meta['author'] or 'unknown'} ({meta['date'] or 'no date'})")

    body = find_body(soup)
    # The genuine paywall gate Substack appends after a preview matches
    # `.paywall` / the Paywall component. `.paywall-jump` is just an in-content
    # anchor present even for subscribers, so it must NOT count — including it
    # produces a false "paywalled" warning on fully-captured paid posts.
    if soup.select_one(".paywall, [data-component-name='Paywall']"):
        print("⚠  this post appears paywalled — only the free preview was captured.")
        print("   To get the full article: open it in your logged-in browser, save the")
        print("   page (Cmd+S → 'Webpage, Complete' or single HTML), and run this tool")
        print("   on the saved .html file — or supply --cookies cookies.txt")

    notes = process_footnotes(soup, body)
    clean_body(body)

    with tempfile.TemporaryDirectory() as tmpdir:
        n_images = embed_images(body, base_url, session, tmpdir)
        print(f"→ embedded {n_images} image(s), {len(notes)} footnote(s)")

        # The URL to credit: the source itself if given as a URL, otherwise the
        # canonical URL recovered from a saved HTML file (skip the bare fallback).
        display_url = ""
        if args.source_url:
            if re.match(r"^https?://", args.source):
                display_url = args.source
            elif base_url and base_url != "https://substack.com/":
                display_url = base_url

        final_html = build_html(meta, body, notes, source_url=display_url)

        if args.output:
            out = args.output
        else:
            pub = publication_slug(base_url, meta)
            out = os.path.join(source_output_dir("substack", pub),
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
