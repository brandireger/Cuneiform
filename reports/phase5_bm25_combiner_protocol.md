# BM25 + frozen-candidate combiner — pre-registered protocol

**Status: PRE-REGISTERED 2026-08-04, written and committed BEFORE the run.**
Authorized by Ixca ("lets run the combiner test"). Training-free; dev split
only; test is never loaded.

## Why this exists

`reports/phase5_ladder_screen_results.md` closed with a reframing, recorded
before this protocol was written:

> The interesting hypothesis is **not** "a pretrained model beats BM25" — on
> this evidence it plainly does not, at 0.37 against 0.63. It is "**does BM25
> + candidate beat BM25 alone?**"

That question is currently answered only by an **oracle** — a perfect
per-query selector reaching 0.7214 against BM25's 0.6312 (+0.0902) for
CANINE. An oracle is an upper bound, not a result. This protocol measures how
much of it a *real* combiner recovers, at no GPU-training cost, so that the
two owed Gate-3 proposals are written against a measured gain rather than a
bound.

**This is a decision-support measurement, not a rung.** Nothing here trains,
fine-tunes, or updates any weight. The only quantity fit is a single scalar
mixing coefficient, by grid search, over embeddings that already exist from
the ratified screen. It is the same class of work the screen was ratified as:
forward passes over frozen weights plus classical scoring.

## Data

Identical to the screen, via the same function
(`phase5_ladder_screen.load_dev_fragments`) — no second implementation:
dev-split fragments, real compositions only (bins carry
`main_split='discovery'` and are excluded by that filter), rendered
ATTESTED-only, ≥4 content tokens. 53 compositions. Task A is scored through
`eval_harness.run_task_a`, so leave-one-out parent-doc exclusion,
best-fragment-per-composition ranking, and single-witness handling are the
same code path for every arm.

Evidence policy `catalog_assisted`; semantic fields `token`, `damage_state`,
`cth`. A feature-use manifest is emitted.

## Combiner forms

Both operate on a **per-query row** of the (n_queries × n_candidates) score
matrix. BM25 scores and cosine similarities are on incomparable scales, so
each row is z-normalized across candidates before mixing. Row-wise
z-normalization is strictly monotone, so it cannot change either input's own
ranking.

- **Primary — linear.** `combined = z(bm25) + α · z(cosine)`, α ≥ 0 fit per
  fold by grid search over
  `{0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0}`.
  **α = 0 is in the grid deliberately**: it recovers BM25's ranking exactly,
  so the combiner family strictly contains the baseline and any held-out gain
  is attributable to the added signal rather than to reparameterization.
  Ties in the fit resolve to the **smallest** α — ties favour BM25 alone.
- **Reference — reciprocal rank fusion.** `RRF = 1/(60 + r_bm25) + 1/(60 +
  r_cos)`, the standard k = 60, no fitting. Reported so that a null result
  cannot be dismissed as an artifact of one fusion form, and a positive one
  cannot be attributed to the fitting procedure.

## Fold structure

Five **composition-level** folds, matching `p2e3`'s convention (`folds: 5`).
Compositions are assigned greedily to the currently-smallest fold in
descending query-count order — deterministic, and balanced by query count
rather than by composition count.

Only the **query** set is partitioned. The candidate pool is always the full
dev set, because a query must be able to retrieve its sibling witnesses; the
combiner sees no candidate labels, and the only fitted quantity is α. α for
fold *f* is fit on the queries of the other four folds and applied to fold
*f*'s queries, which it has never seen.

Pooling the five held-out evaluations covers every query exactly once, each
scored under an α fit without it. Both the fit-set and held-out numbers are
reported, so the transfer gap stays visible — the convention adopted after
the p2e9 dev-only calibration overstated by ~13 points.

## Primary candidate and secondaries

- **Primary: CANINE-s.** Named in advance by the screen's own recommendation
  ("should lead with CANINE"): highest frozen score, the only CI clearing the
  screen threshold outright, largest complementary set (78 queries), largest
  oracle headroom.
- **Secondary: XLM-R base.** Reported in full, no decision weight.
- **Secondary: joint CANINE + XLM-R**, `z(bm25) + α₁·z(cos_canine) +
  α₂·z(cos_xlmr)`, same fold discipline over the product grid. Declared here
  so it is not an after-the-fact addition; no decision weight.

## Pre-registered decision rule

Primary metric: **pooled held-out Task A recall@1**, paired per query against
BM25 on the identical query set.

> The oracle headroom is judged **REALIZABLE** if and only if, for CANINE:
>
> 1. the paired bootstrap 95% CI on (combiner − BM25) held-out recall@1
>    **excludes zero**, and
> 2. the point estimate is **≥ +0.010** absolute.
>
> If either fails, the headroom is judged **NOT REALIZABLE** and the ladder
> question closes: no Gate-3 proposal for rung 4 or rung 6 is written on
> retrieval grounds.

Both clauses must hold — the same two-clause structure as the P4-F falsifier,
and for the same reason: significance without magnitude does not justify a
training rung, and magnitude without significance is not a measurement.

The +0.010 margin is set against the +0.0902 oracle: a combiner recovering
under ~11% of the available headroom does not warrant fine-tuning a
pretrained model on a single consumer GPU when the actual paper blocker is
the first specialist session. Bootstrap: 1,000 replicates, seed 20260722
(`eval_harness.SEED`), resampling queries.

## Verification required before any number is reported

- **α = 0 identity control.** The combiner at α = 0 must reproduce BM25's
  per-query records exactly. If it does not, the normalization or the matrix
  alignment is wrong and every downstream number is void. This mirrors the
  screen's check that `precomputed_scores` handed BM25's own matrix
  reproduces the BM25 path.

## What a positive result would and would not license

**Would**: justify writing the CANINE Gate-3 proposal, framed as *BM25 +
CANINE vs BM25*, with this dev-side gain as its pre-registered expectation.

**Would not**: authorize training. Advancing is still not authorization,
exactly as in the screen. It would also not license any test-side claim — the
gain is measured on dev, on 53 compositions, against a BM25 reference
(0.6312) that is *not* the published test-side figure (0.7831), and absolute
numbers here are not comparable to published ones.

**A negative result is a real finding and will be reported as one**, not
buried: it would mean the 78 complementary queries are not identifiable
without knowing the answer, which is the more informative outcome for the
paper's claim-limits section.

## Contamination

Unchanged from the screen and still owed before any *published* claim. It
does not gate this measurement: a null result needs no contamination
explanation, and a positive one would have contamination as a required
section of the proposal it justifies. Noted here so the sequencing is on the
record rather than inferred.
