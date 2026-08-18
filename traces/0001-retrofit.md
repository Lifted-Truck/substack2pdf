# trace 0001 — retrofit to kit 2.5.0

- **Date:** 2026-08-18
- **Change:** Retrofit substack2pdf from `pre-2.0.0` to kit 2.5.0 (Decisions 1, 4).
  The kit released 2.5.0 mid-run; its one requirement (`.gitattributes` TRACKED)
  was already satisfied, so the declaration was bumped and `.kit/` re-synced.
- **What changed (all created unless noted):**
  - `CLAUDE.md` (charter + `## Mailbox`), `ROADMAP.md`, `DECISIONS.md`,
    `project.manifest.json`, `INDEX.md`, `LIBRARY.md`, `traces/`.
  - `verify` (project-owned, exec bit set, sources `.kit/kit-gates.sh`).
  - `.kit/kit-gates.sh` + `.kit/MANIFEST` — vendored via `kit_sync.py` (kit 2.5.0,
    byte-identical to canonical; `migrate_to_vendored.py` reported already-vendored).
  - `.github/workflows/ci.yml` — `verify fast` on ubuntu.
  - Modified: `.gitignore` (+`.harness/`; deliberately NOT ignoring
    `.kit-currency-plant-*`), `README.md` (dated last-verified line + ROADMAP link).
  - Untouched: `substack2pdf.py`, `docs/`, `.gitattributes` (already conforming).
- **Why:** `currency.py` reported the repo behind by 5 entries; the delta was the
  plan. Gate entries (2.2.0/2.3.0/2.4.0) satisfied by vendoring rather than
  hand-writing `leak_gate`.
- **Evidence / verification:**
  - `./verify fast` → exit 0; sources `.kit/kit-gates.sh`.
  - Gate-fires proof: planted `/Users/<name>/…` in an untracked scratch file →
    `verify fast` went red naming the file (exit 1); removed → green.
  - `currency.py` at close: CURRENT, nothing to do (pasted in the Step 6 notice).
- **git:** committed on `main` (not pushed — pushes are the human's).
