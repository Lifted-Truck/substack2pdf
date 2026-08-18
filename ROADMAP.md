# ROADMAP — substack2pdf

Single source of truth for task state, acceptance criteria, and phase gates.
Ratified choices and their *why* live in [DECISIONS.md](DECISIONS.md); durable
working lessons in [LIBRARY.md](LIBRARY.md).

**Status (last verified 2026-08-18):** Substack support is shipping and
validated against 120+ live articles (free and paid). The repo was retrofit to
kit 2.5.0 on 2026-08-18 (Decisions 1, 4). Everything from Phase 1 onward is
planning. The architecture target is diagrammed in
[docs/architecture.png](docs/architecture.png).

Phase state lives here only; `project.manifest.json` carries no status prose
(kit Decision 28).

---

## Phase 0 — Prior-art landscape (kit bookend, Decision 30)

Standard opening phase: survey the field before committing design, findings
dated and cited in `docs/prior-art.md`.

- **Light pass — done (informal).** Known prior art: other substack-to-PDF
  scripts and browser "print to PDF"; generic readability extractors
  (`trafilatura`, `readability-lxml`) as the multi-platform fallback; WeasyPrint
  vs. headless-Chrome as the render engine. These already inform the design.
- [ ] **Formal landscape + `docs/prior-art.md`** — required *before* Phase 3
  (the adapter/multi-platform work), where the design space genuinely widens.
- [ ] **Test-harness debt (retrofit carry-over).** No fixture goldens yet;
  `./verify` runs `py_compile` only. Add saved-HTML fixtures (free, paywalled,
  footnote-heavy, image-heavy) asserting: body-char floor, no trailing divider,
  no false paywall warning, expected footnote/image counts. *Acceptance:*
  `./verify full` runs the fixtures strictly and is green.

## Phase 1 — Built-in batch

- [ ] Accept multiple URLs / a publication root / a URL file; enumerate via the
  archive API + sitemap (reconcile the two — the archive API paginates in short
  pages). Resolve Substack reader-style URLs and bare post IDs (the
  `.../post/p-<id>` form) to their canonical `/p/<slug>` URL automatically.
- [ ] Pacing, backoff, `--skip-existing`, and a JSON manifest for resume.
- *Acceptance:* one command syncs a whole publication idempotently; re-run
  downloads nothing already present.

## Phase 2 — Formatting levers

- [ ] Factor the hardcoded `CSS` into a theme (page size, margins, fonts,
  line-height, link style, divider glyph, footnote layout) driven by a config
  file + CLI flags. `--source-url` was the first such lever.

## Phase 3 — Adapter abstraction

- [ ] Domain → adapter registry; Substack as the first formal adapter. Gated on
  the Phase 0 formal prior-art pass.

## Phase 4 — MCP server

- [ ] Expose the core as MCP tools (`convert_url`, `list_publication`,
  `convert_batch`) with a job model for long-running batches; cookie paths
  passed by reference, never echoed.

## Phase 5 — More platforms

- [ ] Ghost / WordPress adapters (RSS + content API); `trafilatura` generic
  fallback for arbitrary blogs.

## Phase 6 — Simple GUI

- [ ] Local web app: paste URL(s) or pick a publication, toggle common
  formatting options, watch progress, download PDFs.

## Phase 7 — Formatting studio

- [ ] Advanced GUI: live preview, full theme editor, saved/shareable presets.

## Pre-ship — Prior-art & IP re-scan (kit bookend, Decision 30)

- [ ] Before any packaged public release/distribution beyond the current source
  repo, re-run the prior-art pass and add an IP/licensing check (redistribution
  of paid content is the risk to keep bounded — archiving one's own
  subscriptions is the defensible use). Findings appended to `docs/prior-art.md`.
