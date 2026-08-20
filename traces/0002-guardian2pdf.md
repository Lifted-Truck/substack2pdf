# trace 0002 — guardian2pdf

- **Date:** 2026-08-18
- **Change:** New `guardian2pdf.py` converting theguardian.com articles to PDF
  (Decision 5). `verify` now compiles and imports both converters.
- **Why:** A second publication was requested. Implemented by reuse, not by
  building the Phase-3 adapter registry from one example.
- **Evidence consulted:**
  - Probed the live article's DOM: body is `[data-gu-name="body"]` (~30.7k chars);
    metadata from `og:title`, `[data-gu-name="standfirst"]`, JSON-LD author,
    `article:published_time`.
  - Confirmed the EXISTING `best_image_url` already selects Guardian master-
    resolution images unmodified — the reason reuse was viable.
- **Verification:**
  - End-to-end on the requested long read: 16 pages, 5 images, byline and date
    correct; visual check of p1 and an interior page (image + caption + credit).
  - Body capture 30,155 chars vs 30,155 in the source article container (chrome
    excluded); "Reuse this content" tag/share bar confirmed absent.
  - Trailing-chrome stripper unit-checked against a synthetic prose list to prove
    it does NOT over-strip real content.
  - Gate proven by effect: planted a syntax error in `guardian2pdf.py` →
    `./verify fast` exit 1; restored → exit 0.
  - `./verify fast` and `./verify full` green.
- **git:** committed on `feat/guardian2pdf`; PR opened, not merged.
