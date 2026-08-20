# trace 0003 — output partitioned by source

- **Date:** 2026-08-18
- **Change:** Default output path becomes `output/<platform>[/<publication>]/`
  (Decision 6). New shared helpers `source_output_dir()` and
  `publication_slug()` in `substack2pdf.py`; `guardian2pdf.py` uses the former.
- **Why:** A flat `output/` could not distinguish sources once a second
  converter existed.
- **Evidence / verification:**
  - `publication_slug` unit-checked on four shapes: `*.substack.com` subdomain,
    a custom domain, the saved-HTML fallback base (falls back to `og:site_name`),
    and no-signal-at-all (→ `unknown`).
  - End-to-end: three articles across two platforms landed in
    `output/substack/samkriss/`, `output/substack/astralcodexten/`,
    `output/guardian/`.
  - Migration of 122 pre-existing flat PDFs was dry-run first, then executed:
    120 moved, 2 stale duplicates removed, 0 left flat. Routing read each PDF's
    embedded `Source:` URL, so no file's origin was guessed; this correctly
    split out a Harper's cross-post.
  - `./verify fast` and `./verify full` green.
- **git:** committed on `feat/per-source-output`; PR opened, not merged.
