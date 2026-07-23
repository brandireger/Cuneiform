# SANDBOX_RULES.md — Governance for exploratory work (Phase 2)

Ratified jointly (Ixca + architect session) 2026-07-22. Phase 1's
governance was built for CONVICTION: pre-registered gates, stop rules,
automatic fallbacks, joint-call reservations. That was correct for a
phase making claims. Exploration needs different rules — and applying
conviction-governance to exploration is itself a failure mode, because
pre-registering a success gate on a question you don't yet understand
is how frame lock happens.

These rules are lighter on purpose. Four things carry over unchanged;
everything else relaxes.

## Carried over unchanged (the floor)

1. **Test-side purity is absolute.** No probe, no exception, no
   "just to look." The test side is spent once, in a future P6, on a
   formulation we have chosen deliberately.
2. **Tracers before any scoring pass.** `00_tracers.py` runs first;
   its block goes at the top of the writeup. Any NEW content-consuming
   scorer must have a T1 (scramble-sensitivity) tracer written for it
   BEFORE its first numbers are reported. This rule exists because E2
   produced a full phase of confident numbers from a model reading
   blank pages.
   **Phase 2 clarification (2026-07-23):** the perturbation must change
   the representation the scorer actually consumes. Sequence scorers
   use token-order permutation. Order-invariant bag-of-words scorers
   use deterministic token-identity corruption while preserving input
   length. Permuting order alone is mathematically invisible to BM25
   and cannot establish content sensitivity.
3. **Contracts at ingress.** C1–C10 apply by default to new code.
   C1 (UNK rate) and C7 (bilateral seam content) are the two that
   would have caught Phase 1's worst bug; do not skip them for
   "quick" scripts. Quick scripts are where the bug lived.
4. **Canonical implementations.** `encode_fragment_window()` for
   encoding; the canonical universe loader for fragments; declared
   universes for corpus statistics. No local re-implementations —
   this rule was written in blood three times.

## Relaxed for exploration

5. **No pre-registered success gates on probes.** A probe reports
   what it found. It does not pass or fail. If a probe's result is
   ambiguous, that is a finding about the question, not a verdict
   requiring adjudication.
6. **Kill criteria are time-boxed, not metric-boxed.** Each probe
   declares a wall-clock budget up front (typically 2–8 hours of
   work). When the budget is spent, the probe reports whatever it
   has — including "inconclusive, here's why" — and stops. No
   extensions without a fresh decision; no open-ended chases.
7. **Negative results need no ceremony.** A probe that finds nothing
   is a completed probe. Write three paragraphs, not three sections.
   No errata process, no branch tree, no joint call required.
8. **Provisional numbers are allowed, and must be labeled.** Mark
   exploratory numbers `[PROBE — not for citation]`. They may be
   rough, single-seed, small-n, and uncorrected. What they must never
   be is *unlabeled*, because Phase 1's most expensive errors came
   from provisional numbers hardening into cited facts.
9. **One-way doors still require a joint call.** Anything that
   cannot be undone — touching test data, migrating the corpus,
   changing frozen splits, contacting the TLHdig team, publishing —
   stops for Ixca. Everything reversible proceeds without check-in.
10. **Probes may be abandoned mid-flight.** If a probe reveals its own
    question was malformed, say so and stop. Sunk effort is not an
    argument for completion.

## Reporting format for probes (deliberately small)

A probe report is at most one page:

- **Question** (one sentence: which of Q1–Q5, and what specifically).
- **What I did** (enough to reproduce; seeds and paths).
- **What I found** (numbers, labeled `[PROBE]`; plots optional).
- **What it rules in / rules out** (the actual payload).
- **Cost** (wall-clock spent vs budgeted).
- **Tracer block** if any scoring occurred.

No acceptance-check lists. No gate tables. If a probe's finding turns
out to be load-bearing for a paper claim, it gets PROMOTED to a
proper measurement with full rigor — and promotion is the moment
conviction-governance reattaches.

## The promotion rule (how sandbox work becomes real)

A probe result becomes a citable claim only after:
1. Re-run under the full contract/tracer regime, seeded, with n and
   CIs stated;
2. An explicit statement of which universe/statistics it used;
3. A joint call to promote (this is the one place Phase 2 keeps
   Phase 1's ceremony, because it is where exploration turns into
   assertion).

Anything not promoted stays labeled `[PROBE]` forever, including in
internal notes. There is no third category.

## Anti-frame-lock provisions (new, and the reason this file exists)

11. **Every probe report ends with one sentence naming what would
    have to be true for its conclusion to be WRONG.** Not a caveat
    paragraph — one specific falsifier.
12. **Any probe may propose that a different question should be asked
    instead.** That proposal is a legitimate deliverable, equal in
    standing to results. Phase 1's most valuable moment came from
    stepping outside its own frame; this makes that a normal move
    rather than a rescue.
13. **Periodic premise audit.** At roughly every third probe, or
    whenever three consecutive probes come back null, stop and ask
    explicitly: *are we still asking the right question?* Schedule
    it; do not wait for someone to feel uneasy. Governance can audit
    procedure but not premises — only a scheduled pause can.
14. **Attribution over narration.** If a cause is proposed for any
    observation, either measure it or label it a guess. The phrase
    "almost certainly" is banned from probe reports. (Twice in Phase
    1 an architect-narrated attribution measured exactly zero.)

## Budget posture

- CPU/inference: unrestricted within probe time-boxes.
- GPU training: **none authorized by default.** Any probe that wants
  gradient updates stops and asks first, with a named hypothesis, a
  time-box, and a falsifier. The D17b 12h budget released by
  P5_CLOSEOUT is not pre-allocated to anything.
- Human time (Ixca's): the scarce resource. Probes should be
  designed to be reported in one page and understood in five minutes.
