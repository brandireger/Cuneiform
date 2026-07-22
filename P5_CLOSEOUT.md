# P5_CLOSEOUT.md — Formal close of Phase 1 (P3–P5C)

Ratified jointly (Ixca + architect session) 2026-07-22. This document
ends Phase 1, suspends its remaining machinery, states its results as
final, and hands the durable assets forward to Phase 2. Nothing here
is a failure report; it is a closing of accounts.

## 1. What is suspended, effective immediately

- **D17c (M1/M2 diagnostics): SUSPENDED, not cancelled.** Its
  authorization stands on paper but is not to be executed. Reason:
  it diagnoses *why the boundary head prefers negatives* inside a
  frame Phase 2 abandons. The sighted evidence (below) makes the
  question less interesting than the question of whether the head
  was ever asked a well-posed question at all — which is Phase 2's
  P2-A probe.
- **D17b (conditional retrain, ≤12h GPU): SUSPENDED.** Its
  precondition (a live M1/M2 verdict) will not be produced. The 12h
  budget is released back to Phase 2.
- **The automatic fallback clause: EXECUTED, in the sense that
  matters.** BM25-retrieve-deep is the shipping retrieval+ranking
  stage. No further Phase 1 training rounds.
- **P6 (test-side final runs): DEFERRED to Phase 2's decision.** The
  test side remains untouched. What P6 eventually measures depends
  on what Phase 2 concludes is worth measuring; running it now would
  spend the one-shot budget on a formulation we no longer believe is
  the right one.

## 2. Phase 1 results, final

### 2.1 The system that works

BM25 over sign-level tokenization, full-distractor scale, dev joins
(n=182): **recall@1 = 0.6758, recall@10 = 0.8077, recall@200 =
0.896**. Duplicates (n=872): recall@1 = 0.3727, recall@10 = 0.6835;
Task A composition assignment (test-side, n=793): recall@1 = 0.7831
(bm25_sign) / 0.8184 (bm25_lemma). This is the shipping system. It
requires no GPU.

The frozen P3 test-side baseline — the "number to beat" cited
throughout — stands unchanged: **tier-A joins recall@1 = 0.0588
(test_only), 0.0000 (full_distractor)**, n=34 test-side tier-A pairs.

### 2.2 The negative results (final, and the phase's real output)

1. **Dense bi-encoder retrieval (D15) underperforms BM25, and the
   gap widens with index scale.** Dev joins recall@10: BM25 0.835 vs
   best bi-encoder 0.571 at test_only scale; 0.808 vs 0.396 at
   full_distractor. Gap 0.264 → 0.412. Complementarity is
   essentially nil: at k=10, dense-only hits = 1 of 182; RRF fusion
   (0.769) underperforms BM25 alone (0.808). Encoding path verified
   CLEAN by execution (0.12% UNK), so this result is about the
   method, not the plumbing.
2. **The frozen boundary head (D14) does not discriminate true join
   partners from BM25-mined lexically-similar non-partners on real
   content.** Sighted: seam_score positives 0.4680 ±0.1597 vs
   negatives 0.4804 ±0.1411 — negatives marginally higher,
   distributions heavily overlapping. Cascade regresses BM25 on
   every gate (G1 joins @1 0.1978 vs 0.6758; G4 duplicates @1
   0.1216 vs 0.3727).
3. **Short-horizon edge-continuation lift (D18) is negative on
   average.** H=5 mean lift = −0.110 across 206,551 dev pairs;
   tracer T4 independently failed at canary scale (1/5, cross-checked
   2/5). The span-infilling capability it rests on collapses with
   span length: exact-match 0.413 at length 1, 0.111 at 2, 0.024 at
   3, 0.002 at 5, 0.000 at 6+.
4. **Tier-A joins are not solved, or approached, by anything built.**
   Sighted cascade tier A: recall@1 = 0.0, recall@10 = 0.0 (n=27
   dev). BM25 ceiling@200 for tier A = 0.519 — half of true tier-A
   partners never surface in a 200-deep lexical net.

### 2.3 The structural finding that motivates Phase 2

From the fracture engine's own calibration: **tier A/B joins have
n_shared_lines ≈ 0 by definition — "that IS the no-overlap seam
signature."** Combined with the 0.519 ceiling and the tier-A zeros,
Phase 1's honest conclusion is: *for the hardest and most
scientifically interesting joins, the lexical overlap signal is
absent by construction, and no learned component built here recovered
a substitute for it.* Whether a substitute exists in this data at all
is Phase 2's opening question.

### 2.4 Three bugs, caught and documented

- **H1 family-exclusion**: composite-doc siblings shared a
  `parent_doc`, so every join query's true partner was silently
  excluded; patched tables read 0.0 and were briefly read as "hard
  task." Fixed; `results_p3_patched_v2/` emitted; v1 retained and
  marked SUPERSEDED; erratum in `h1_patch_report.md`.
- **IDF reference drift**: BM25 statistics fit over a query-derived
  candidate union (15,153) rather than the declared universe
  (21,920). Both architect-named candidate causes measured *exactly
  zero*; the true cause was a third, unnamed mechanism. Convention
  now codified in CLAUDE.md.
- **E2 content-blind scoring**: five scripts each reimplemented
  `flatten_lines`, pushing `(token, damage_state)` tuples into
  `Tokenizer.encode()` where a defaulting `.get()` absorbed them —
  82.6% `<UNK>`. All D17/D18/D19 numbers prior to 2026-07-22 measured
  a model reading blank pages. Fixed via canonical
  `encode_fragment_window()`; strict mode added; superseded numbers
  annotated in place.
- **A fourth, scoped and open**: P4B's B5 real-pair half fed
  `sign_attested` (word/compound grain) to the decomposed per-sign
  vocabulary — 13.9% UNK. B5's ~0.56 correlation is **provisionally
  withdrawn**; B1/B2 (Branch R's evidentiary base) are CLEAN and
  unaffected. Re-run is cheap; do it in Phase 2 or cite nothing.

### 2.5 Corrections to the record already applied

- `p5_report.md` §5 mechanism story: SUPERSEDED annotation.
- `p5_report.md` §8 "convergent negative finding": DOWNGRADED to its
  single verified leg (D15/B1/B2).
- `P5C_SPEC.md` standing facts: corrective note appended.
- `CLAUDE.md`: encoding convention + corpus-statistics convention.
- `data_card_notes.md`: superseded-scores line; demo never displayed
  them ("Edge fit: pending P5" was literally true throughout).

## 3. Durable assets carried into Phase 2

Do not rebuild these; they are frozen, verified, and reusable.

| Asset | State | Notes |
|---|---|---|
| Sign-level tokenizer | vocab 2,374; dev OOV 0.16%; round-trip 5/5 exact | Logogram sign-decomposition amendment included |
| `encode_fragment_window()` | canonical, strict-mode enforced | The only legal encoding path |
| `lib/contracts.py` C1–C10 | 20/20 self-tests pass | C4/C9 violation tests replay this project's real bugs |
| `scripts/00_tracers.py` T1–T5 | green except T4 (a true finding, not a defect) | T1 retro-validated: 0/8 pre-fix, 8/8 post-fix |
| Fracture engine + calibration | distribution-matched to real marginals | Gap-width sampling is a documented Poisson assumption, NOT corpus-calibrated |
| D14 encoder checkpoint | frozen, 12.8M params, 60k steps | Boundary AUC in-doc 0.746; span-infill 0.413@len1 |
| BM25 pipeline (whole + edge-window N=3) | union candidate set, ceiling 0.918 | Edge-window union raised ceiling +0.022 |
| Hard set | n=46, frozen, seed 20260722 | Bottom-quartile BM25-score-to-partner |
| Eval harness + splits | frozen, H1-corrected | git 7b010cde splits; test untouched |
| Demo track (Takšan) | fully spec'd, BM25-backed, unaffected | Continues on current rails |

## 4. Publication posture (recommendation, not a decision)

Phase 1 supports an honest paper today: a strong lexical baseline
with measured ceilings, four rigorously-established negative results,
tier-stratified reporting that separates the easy majority from the
hard core, and an audit trail of four caught bugs with errata. The
claim to avoid is any version of "neural methods fail on Hittite" —
the supported claim is narrower and better: *at this supervision
scale (182 dev joins, 27 tier-A), on this corpus, these specific
formulations did not beat lexical retrieval, and here is exactly how
we know the measurements are sound.* Phase 2 may add to this; it
does not need to for the work to be publishable.

## 5. Close

Phase 1 delivered a working system, four negative results, a hardened
pipeline, and a demo. It did not deliver a neural improvement, and it
does not claim one. The tier-A problem is open, measured, and handed
forward.

Signed off: Ixca + architect session, 2026-07-22.
