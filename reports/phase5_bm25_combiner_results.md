# BM25 + frozen-candidate combiner — results

**Status: COMPLETE 2026-08-04. The pre-registered rule returns REALIZABLE.**
**Everything here is `[PROBE — not for citation]`; dev split only, test never
loaded.**

Executes `reports/phase5_bm25_combiner_protocol.md` (PRE-REGISTERED and
committed as `50b6455`, before the run). Training-free: no gradients are
computed; the only fitted quantity is one scalar per fold.

## The verdict, by the rule as pre-registered

Primary candidate CANINE-s, pooled held-out Task A recall@1, paired per query
against BM25 on the identical 865-query dev set:

| | recall@1 | recall@5 | MRR |
|---|---|---|---|
| BM25 alone | 0.6312 | 0.8578 | 0.7336 |
| **BM25 + CANINE (α fit per fold)** | **0.6775** | 0.8763 | 0.7692 |
| delta | **+0.0462** | +0.0185 | +0.0356 |

Paired bootstrap 95% CI on the recall@1 difference: **[+0.0254, +0.0682]**.

- Clause 1 — CI excludes zero: **met**.
- Clause 2 — point estimate ≥ +0.010: **met** (+0.0462).

**Verdict: REALIZABLE.** The screen's oracle headroom was +0.0902; a real,
fold-fitted combiner recovers **51.2%** of it.

The identity control passed: at α = 0 the combiner reproduces BM25's 865
per-query records exactly, so the family provably contains the baseline and
the gain is not a reparameterization artifact.

## All arms

| arm | held-out recall@1 | Δ vs BM25 | 95% CI | gained | lost |
|---|---|---|---|---|---|
| **BM25 + CANINE, linear** | **0.6775** | **+0.0462** | [+0.0254, +0.0682] | 72 | 32 |
| BM25 + XLM-R, linear | 0.6647 | +0.0335 | [+0.0092, +0.0578] | 74 | 45 |
| BM25 + both, joint (secondary) | 0.6613 | +0.0301 | [+0.0046, +0.0543] | 76 | 50 |
| BM25 + CANINE, RRF (unfitted) | 0.5595 | **−0.0717** | [−0.1087, −0.0347] | 95 | 157 |
| BM25 + XLM-R, RRF (unfitted) | 0.5503 | **−0.0809** | [−0.1168, −0.0428] | 108 | 178 |

## Four things this does not say

**1. The gain is not free — 32 queries regress.** The +0.0462 is a net of 72
gained against 32 lost. For a system whose product definition is expert
decision support, a composition that BM25 ranked first and the combiner does
not is a real cost, not a rounding error. Any deployment claim must quote
both numbers, not the net.

**2. Equal-weight fusion is much WORSE than BM25 alone.** RRF, the
parameter-free reference, loses 7–8 points. This was implemented fairly —
ranks are taken *within each query's eligible pool*, not over the full pool
before masking, because RRF's sum of reciprocals is not invariant to removing
candidates that sit at different depths in the two lists. So the failure is
the method's, not the implementation's.

The reading is specific and matters for the proposal: **the candidate is
useful only as a down-weighted tie-breaker.** Fitted α landed at 0.5 on
z-scores — CANINE gets half the weight of BM25. Treat the two as co-equal
evidence and the result inverts. Whatever a Gate-3 proposal tests, the
mixing weight is load-bearing and cannot be assumed.

**3. The transfer gap is structurally zero and proves nothing.** CANINE's α
selected as **0.5 in all five folds**, so the fit-set and held-out pools are
the same queries under the same matrix, and their difference is 0.0000 by
construction. That number is uninformative and the script now labels it so.
What *is* informative is the stability itself, and the per-fold breakdown:

| fold | n | α* | held-out Δ vs BM25 |
|---|---|---|---|
| 0 | 255 | 0.5 | +0.0706 |
| 1 | 152 | 0.5 | +0.0132 |
| 2 | 152 | 0.5 | +0.0658 |
| 3 | 153 | 0.5 | +0.0458 |
| 4 | 153 | 0.5 | +0.0196 |

**All five folds are positive**, so the pooled gain is not an average
concealing one fold doing the work. Fold-level recall differs widely
(0.588–0.804) because compositions differ in witness count, but the
comparison is paired per query, so that difficulty cancels.

XLM-R is weaker on both counts: α moved across folds (1.0/1.0/0.75/0.75/0.75)
and **fold 1 is negative** (−0.0066). Its advance was already the thinner one
in the screen, and it still is.

**4. Adding XLM-R on top of CANINE makes things worse.** The joint arm
reaches +0.0301 against CANINE-alone's +0.0462, and its fitted weights are
unstable across folds (α_canine ranges 0.1–0.75; fold 4 sets α_xlmr to 0).
Two parameters on 53 compositions is more freedom than this data supports.
**No evidence the two candidates contribute independently** — consistent with
their 75.7% / 80.6% redundancy with BM25 measured in the screen.

## What this changes for the owed Gate-3 proposals

It sharpens them considerably, and it raises the bar rather than lowering it.

The +0.0462 is available **now, with frozen weights and no GPU training**. So
a rung's marginal question is no longer "does a pretrained model help?" — that
is answered, yes, modestly, as a re-ranking signal. It becomes:

> **Does fine-tuning CANINE beat the frozen CANINE combiner's +0.0462?**

That is a harder, narrower and more falsifiable hypothesis than the one the
screen left, and it is the one a rung-4 proposal should pre-register. A rung
that merely matches the frozen combiner would not be worth its GPU budget.

**Advancing is still not authorization to train.** No proposal has been
written and no training has been started.

## FOLLOW-UP — this is a Task A result and does not clearly transfer

`reports/phase5_combiner_taskb_results.md` (2026-08-04) ran the same
combiner on Task B under the standing three-way rule. **Joins +0.0165 (CI
[−0.0165, +0.0495]) and duplicates +0.0197 (CI [−0.0023, +0.0416]) — neither
individually significant.** Only the pooled cell excludes zero, and that is
the cell the three-way rule exists to prevent reporting alone.

Nothing above is retracted: the Task A measurement stands as made. But
"+0.0462" must always be qualified by the task it was measured on, and may
not be cited as a general retrieval gain.

## Standing limitations

- **Dev-side only, 53 compositions.** The BM25 reference here is 0.6312; the
  published test-side figure is 0.7831. Absolute numbers are not comparable
  across those sets, and only the within-run comparison is meaningful. There
  is no claim that +0.0462 transfers to the test side.
- **Folds partition queries, not the candidate index.** A query must be able
  to retrieve its sibling witnesses, so the candidate pool is always the full
  dev set. With a single scalar fitted, the exposure is small — but this is
  not a fully held-out index and should not be described as one.
- **Contamination remains unresolved** (screen, "Contamination is now a live
  concern") and is now *more* load-bearing, because there is a positive
  result to explain. It stays a required section of any proposal. The most
  parsimonious account of a character-level model helping a lexical matcher
  is orthographic similarity, which needs no memorisation — but that is an
  argument, not a measurement.
- One seed, one fold assignment, one grid.

## Artifacts

- `scripts/phase5_bm25_combiner.py`
- `Phase4/phase4_out/p5_bm25_combiner.json`
- `Phase4/phase4_out/p5_bm25_combiner_manifest.json` (feature-use manifest,
  `catalog_assisted`)
- `Phase4/phase4_out/p5_combiner_embeddings.npz` (frozen-embedding cache)
