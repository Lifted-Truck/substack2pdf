# DECISIONS — substack2pdf

Append-only decision log (kit 2.0.0). A ratified choice and its *why* land here,
never in ROADMAP. Supersede a decision with a new one that cites it; never edit
or delete a past entry. Newest at the bottom.

---

## 1 — Retrofit to kit 2.4.1 (2026-08-18)

**Decision.** Bring this repo onto the ecosystem harness kit at version 2.4.1:
charter (`CLAUDE.md` with `## Mailbox`), `ROADMAP.md`, this log,
`project.manifest.json`, the knowledge loop (`INDEX.md` + `LIBRARY.md`),
`traces/`, a project-owned `./verify` sourcing vendored `.kit/kit-gates.sh`, and
CI. Architecture rung 1 (single thread), confirmed by the human.

**Why.** `currency.py` reported the repo `pre-2.0.0`, behind by 5 entries. The
gate entries (2.2.0/2.3.0/2.4.0) are satisfied by vendoring `.kit/` rather than
hand-writing a `leak_gate` — a copied gate is exactly the drift the vendoring
model exists to end (kit CHANGELOG 2.4.0). Non-destructive: no existing file was
rewritten; `substack2pdf.py` and `docs/` were untouched.

## 2 — Paywall detection asserts effective truncation, not marker presence (2026-06, ratified in retrofit)

**Decision.** The "only the free preview was captured" warning fires on
`.paywall` / the `Paywall` component only — NOT `.paywall-jump`.

**Why.** `.paywall-jump` is a benign in-content anchor present even for
authenticated subscribers, so counting it produced a false warning on
fully-captured paid posts. The real gate sits *outside* the article body; the
benign anchor sits inside. Asserting the effective state keeps the warning
honest with and without cookies. Evidence: [[LIBRARY.md]] L0001.

## 3 — Never commit credentials or generated output (2026-06, ratified in retrofit)

**Decision.** `cookies.txt` (a credential granting access to logged-in
accounts), generated PDFs, and saved input HTML are gitignored and never
committed or pushed. The repo is public.

**Why.** A cookie file is a live credential; generated PDFs may contain paid
content. Enforced by `.gitignore` and, for machine-identity paths, the
`leak_gate`.

## 4 — Declare kit 2.5.0 (2026-08-18)

**Decision.** Bump `kit_version` from 2.4.1 to 2.5.0 and re-sync `.kit/`.

**Why.** The kit released 2.5.0 mid-retrofit (`.gitattributes` must be TRACKED,
not merely present). `currency.py` showed the repo already SATISFIED that
requirement — `.gitattributes` was committed earlier — so only the declaration
was stale. Per the kit's Step 5 rule a repo declares a version exactly when it
meets every requirement, so the honest move was to bump rather than leave a
true-but-understated declaration. No behaviour changed; cites Decision 1.

## 5 — A second converter reuses the renderer rather than abstracting it (2026-08-18)

**Decision.** Add `guardian2pdf.py` for theguardian.com as a sibling script that
imports substack2pdf's shared machinery (`make_session`, `embed_images`,
`build_html`, `slugify`, `_ensure_native_libs`, `OUTPUT_DIR`) and implements only
its own `fetch_html` / `extract_metadata` / `find_body` / `clean_body`. No
adapter registry yet.

**Why.** "Reduce, never invent": the rendering half already worked unchanged on
Guardian markup — the existing `best_image_url` picked the Guardian's master-
resolution images with no edits — so duplicating ~200 lines to gain a second
publication would have bought nothing. Building the full Phase-3 adapter
abstraction from a single new example would be inventing an interface from one
data point. The `from substack2pdf import …` coupling is deliberate, recorded
debt, and is what ROADMAP Phase 3 repays once a third publication shows what the
interface actually needs.

**Also decided.** Guardian chrome is detected STRUCTURALLY (a trailing block with
no prose, whose text is mostly link text), never by class name: Guardian class
names are hashed (`dcr-…`) and change between deploys, so a class match would
silently rot. First attempt counted `<li>` as prose and kept the very tag list it
meant to drop — see [[LIBRARY.md]] L0003.

## 6 — Output is partitioned by source (2026-08-18)

**Decision.** PDFs default to `output/<platform>[/<publication>]/` —
`output/substack/samkriss/…`, `output/guardian/…` — instead of one flat
`output/`. `-o` still overrides with an explicit path.

**Why.** A flat folder stopped scaling the moment a second source existed: 120
posts from one newsletter sat beside unrelated articles with no way to tell them
apart but the filename. Platform-then-publication (rather than publication alone)
matches the shape ROADMAP Phase 3 will formalise, so the adapter registry can
own this path later without moving anyone's files a second time.

**Also decided.** The publication is derived from the URL host, not from
`og:site_name` — the host is present and stable on every fetch, while the meta
tag is sometimes absent or generic. `og:site_name` remains the fallback for
saved-HTML input, where the recovered base URL may name no publication.

**Migration.** The 122 existing flat PDFs were routed by reading the `Source:`
URL each file already carries (the `--source-url` feature), so placement was
derived per file rather than assumed — which is how the Harper's cross-post
landed in its own folder instead of being lumped in with the newsletter it was
downloaded alongside.

## 7 — Network failures exit with one line, not a stack trace (2026-08-18)

**Decision.** Both converters route URL fetches through a shared `http_get()`
that turns HTTP and network errors into a one-line `error:` message plus the
offending URL, and exits. Distinct hints for 404, 403 (suggests `--cookies` or a
saved page) and 429 (rate limit).

**Why.** A traceback is the wrong output for "that page does not exist": it
buries the single fact the user needs under frames from inside `requests`, and
reads as a crash in the tool rather than a problem with the input. Observed:
a user pasted a placeholder URL from the README and got a `requests.HTTPError`
traceback, which is indistinguishable from a bug.

**Also decided.** The README's Guardian example is now a real, working article
URL. The previous placeholder (`.../2026/aug/18/some-article`) sat on the real
`theguardian.com` domain, so it read as genuine and 404'd when copy-pasted —
the direct cause of the report above. An example on a real domain must either
work or be unmistakably fake.

**Also decided.** The URL recorded in the PDF is stripped of tracking parameters
(`utm_*`, `CMP`, `fbclid`, …) while functional ones (e.g. `page=2`) are kept, so
an archived article carries a clean canonical reference rather than the campaign
noise of whichever mailout it arrived in.
