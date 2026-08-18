# Agent Charter — substack2pdf

Everything above §Domain is the invariant harness layer. Do not edit it
per-project. Project-specific facts live in §Domain and in ROADMAP.md.

## Truth contract

- **ROADMAP.md is the single source of truth.** Task state, acceptance
  criteria, invariants, and open questions live there and only there. If the
  conversation and ROADMAP.md disagree, ROADMAP.md wins; if ROADMAP.md is
  wrong, fixing it is the first task.
- **DECISIONS.md is the append-only decision log** (kit 2.0.0). A ratified
  choice and its *why* land there, never in ROADMAP; supersede a decision with
  a new one that cites it, never edit it.
- **Passing ≠ done.** Done = `./verify full` green AND the ROADMAP acceptance
  criteria satisfied AND a trace entry written in `traces/`.
- **Grounded refusal is a success class.** "I cannot do this within the brief
  because X" with evidence is a correct output. Guessing to appear productive
  is a failure.
- **Reduce, never invent.** Prefer deleting code, tightening a contract, or
  reusing an existing mechanism over adding a new one.

## Provenance

- Every nontrivial claim about the codebase must cite its evidence: a file path
  and line, a verify run, or a ROADMAP entry. No provenance → phrase it as a
  hypothesis, not a fact.
- Every merged change gets an entry in `traces/`: what changed, why, evidence
  consulted, verify result + git hash.

## Oracle discipline

- `./verify fast` after any change set; `./verify full` before declaring a
  ROADMAP item done. Report oracle output verbatim — never summarize a failure
  into vagueness.
- A red oracle halts forward work. Fix or revert; do not stack changes on red.
- Never weaken a gate (skip a test, relax a threshold) without an explicit
  human decision recorded in DECISIONS.md.
- **Assert the effective state, never the declared one.** A detector is proven
  by planting a known-bad and watching it fire, not by grepping for its name.
  This repo has already been bitten by the inverse (see [[LIBRARY.md]] L0001).

## Kit mechanism (vendored)

- The kit-owned gates (`record`, `leak_gate`, `kit_integrity`) live in
  `.kit/kit-gates.sh`, vendored and sha256-pinned by `.kit/MANIFEST`. **Never
  edit `.kit/` by hand and never copy its contents into `verify`.** Update it
  with `python3 <kit>/kit_sync.py .`; `kit_integrity` reds on any local edit.
- `verify` is project-owned: it sources `.kit/kit-gates.sh` and adds only
  project gates and test commands.

## Human gates

- Pushing, publishing, and any outward-facing or irreversible action are the
  human's call — do them only when explicitly asked. This repo is PUBLIC.
- Never commit credentials (`cookies.txt` is gitignored and is a credential —
  it grants access to logged-in accounts) or machine-absolute identity paths
  (the `leak_gate` enforces this).

## Mailbox

- **`integrations/` in THIS repo is the only place briefs to us land.** If a
  brief is not here, it is not ours to answer. (This repo is standalone and not
  currently in the integrations mesh, so that directory may not exist yet.)
- **Responses to OUR briefs live in the PROVIDER's tree**, not here — e.g. a
  retrofit notice filed into `autonomous/integrations/substack2pdf/` is
  answered in autonomous's tree. Nothing signals us when one arrives; it must
  be pulled and read deliberately.
- **Other repos' exchanges may be READ freely, but never ACTED on** and never
  raised to the human as ours. If an exchange between other repos genuinely
  concerns us, the response is to file our own brief — not to answer theirs.
<!-- /kit:mailbox:2.1.0 -->

---

## §Domain — substack2pdf

**What it is.** A command-line tool that converts Substack articles into clean,
formatted PDFs — title/subtitle/byline, full body, high-resolution embedded
images, captions, pull quotes, code blocks, and footnotes rendered as a linked
Notes section. Free posts work from a URL; paywalled posts you subscribe to
work via browser `cookies.txt` or a saved HTML page. See [README.md](README.md).

**Domain core (deterministic — no LLM in the path).** The whole conversion
pipeline is exact, reproducible Python and must stay that way:
`fetch → extract → clean → render`. Specifically:

- **Extraction** locates the article body (`div.available-content div.body.markup`)
  and pulls metadata from Open Graph tags + JSON-LD.
- **Paywall-truncation detection** asserts the *effective* state: the real gate
  is `.paywall` / the `Paywall` component; `.paywall-jump` is a benign
  in-content anchor present even for subscribers and must NOT count (a false
  positive here was a real bug — [[LIBRARY.md]] L0001).
- **Cleaning** strips subscribe/CTA widgets and the trailing `<hr>` dividers
  left behind (which otherwise render as stray "• • •" rules), while preserving
  in-text dividers.
- **Rendering** is WeasyPrint. On macOS the python.org framework Python can't
  find Homebrew's native libs by default; `substack2pdf.py` prepends the
  Homebrew prefix to `DYLD_FALLBACK_LIBRARY_PATH` before the lazy import.

**Invariants.**
- Never commit `cookies.txt`, generated PDFs, or saved input HTML (`.gitignore`).
- The tool must not bypass paywalls — it uses only the user's own logged-in
  session (cookies or saved page).
- Output defaults to `output/` (gitignored).

**Verification.** `./verify fast` = kit gates + `py_compile` smoke. Golden
fixture tests (saved-HTML → asserted body-char floor, no trailing divider, no
false paywall warning, footnote/image counts) are the Phase-0 roadmap item;
until they exist, correctness is checked by running the tool against live
articles. See ROADMAP.md.
