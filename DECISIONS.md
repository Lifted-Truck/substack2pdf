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
