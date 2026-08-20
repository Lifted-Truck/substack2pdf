# trace 0004 — friendly fetch errors, honest README example

- **Date:** 2026-08-18
- **Change:** Shared `http_get()` and `clean_source_url()` in `substack2pdf.py`,
  used by both converters (Decision 7). README's Guardian example replaced with
  a real article URL.
- **Why:** A placeholder URL from the README produced a `requests.HTTPError`
  traceback, which reads as a tool bug rather than a bad input.
- **Evidence / verification:**
  - The exact failing command now prints a two-line `error:` with the URL and no
    traceback; same for the equivalent Substack 404 (shared helper) and for an
    unreachable host (`ConnectionError`).
  - `clean_source_url` checked both ways: `?CMP=…` and `?utm_*` stripped,
    `?page=2` preserved, no-query URLs untouched.
  - End-to-end on a live Guardian long read carrying `?CMP=GTUK_email`:
    16 pages, 5 images, trailing chrome absent, and the archived `Source:` line
    confirmed free of the tracking parameter.
  - `./verify fast` and `./verify full` green.
- **git:** committed on `fix/friendly-fetch-errors`; PR opened, not merged.
