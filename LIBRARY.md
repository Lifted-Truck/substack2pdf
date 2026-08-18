# LIBRARY — durable, evidence-backed lessons

Long-term memory for this project's knowledge loop. **Repo-shared
agent-process lessons only** — the hard-won, evidenced "how to work in this
repo without re-tripping a wire." Not decisions (→ DECISIONS.md), not task
state (→ ROADMAP.md), not machine-local facts (→ the human's global memory).

Entries are retrieved via [INDEX.md](INDEX.md). Format is `library-entry.3`
(canonical contract: `autonomous/kit/contracts/library-entry.md`). New lessons
enter as `tier: candidate` and become `canonical` on a second independent
occurrence or human review. Every entry states its own **falsifier** — the
observation that would retire it.

**Entry template**

```
[Lxxxx] <title> | tier: … | added: YYYY-MM-DD | tags: … | lesson: … | evidence: … | falsifier: … | supersedes: —
```

## Entries

[L0001] A paywall marker in the page is not a paywall on the content — assert the effective truncation | tier: candidate | added: 2026-08-18 | tags: paywall-detection, extraction-fidelity, gate-discipline | lesson: Substack leaves paywall-related markup in the page even for authenticated subscribers who received the full article. Detecting "was this truncated?" by the mere presence of a paywall selector therefore fires false positives on fully-captured paid posts. Discriminate by the selector that actually gates content (`.paywall` / the `Paywall` component, which sits OUTSIDE the article body) versus the benign in-content anchor (`.paywall-jump`, present for subscribers too). The honest signal is effective: is the body actually short / cut off, not is a marker present. | evidence: 2026-06 — the tool printed "only the free preview was captured" on 8 paid posts whose full text (33k+ body chars vs ~9k for a real preview) had in fact been captured via cookies; the fix dropped `.paywall-jump` from the detector and the warning went quiet with cookies, still fired without them. | falsifier: a Substack truncated preview that carries NO `.paywall`/`Paywall` marker, or a full subscriber article that reliably carries one — either would break the discriminator. | supersedes: —

[L0002] Verify a batch against the source-of-truth listing and the artifacts on disk, never the run's own log | tier: candidate | added: 2026-08-18 | tags: oracle-discipline, extraction-fidelity | lesson: A batch loop reporting "N OK" proves only that the process exited 0 N times — not that the right N items were produced with real content. Confirm completeness by diffing the authoritative listing (the Substack archive API + sitemap, reconciled) against the artifacts actually on disk, and confirm fidelity by measuring the artifact (page/char counts, expected endings), not by trusting the log. This is the kit's "assert the effective state" rule applied to bulk work. | evidence: 2026-06/08 — "23 OK, 0 failed" masked that paid content still needed confirming (checked via on-disk char counts); the archive-vs-disk diff both caught genuinely-missing new articles across sync rounds AND surfaced a `while read` loop silently dropping its last URL because the input file lacked a trailing newline — the run log looked clean. | falsifier: a batch whose own success log is a sufficient completeness proof because the listing and the artifacts cannot diverge from it. | supersedes: —
