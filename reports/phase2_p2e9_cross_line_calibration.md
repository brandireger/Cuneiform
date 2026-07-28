# Phase 2 P2-E9 — cross-line per-rank calibration

Cell `a2_m1` — the cell the real-gap single-sign pipeline applies. Composition-folded, fit on calibration compositions and reported on held-out ones, witness support required from an independent source family.

**A rate here is a property of many past comparisons at that rank in that stratum. It is never the probability that one particular lost reading is true.** Cross-line rates may not be applied to same-line gaps, or the reverse.

## Admission rule: `LAYOUT_AGNOSTIC` (**RATIFIED** 2026-07-28 by Ixca)

Line division is scribal layout, not textual structure: the same phrase may be written on one line in one manuscript and across a break in another, so a same-line witness occurrence is real evidence about a cross-line gap. Measured effect: raw top-1 agreement 24.2% -> 32.9%, gold inclusion 4.27% -> 7.21%, best achievable selector rate 79.7% -> 81.2%.

`STRICT` is retained below as a declared ablation, not deleted: adopting a rule should never destroy the comparison that justified it.

| rule | eligible spans | folds with a usable rule | accepted (held-out) |
|---|---:|---:|---:|
| `LAYOUT_AGNOSTIC` | 78,910 | 5/5 | 8,208 |
| `STRICT` | 61,596 | 5/5 | 2,471 |

### `LAYOUT_AGNOSTIC` — per-rank calibration by fold

| fold | held-out accepts | rank-1 (HELD-OUT) | 95% CI | n |
|---|---:|---:|---|---:|
| 0 | 1,537 | 75.7% | 0.735263–0.778093 | 1,537 |
| 1 | 1,543 | 74.9% | 0.726295–0.769554 | 1,543 |
| 2 | 1,713 | 75.5% | 0.733889–0.774603 | 1,713 |
| 3 | 1,827 | 82.3% | 0.805041–0.840017 | 1,827 |
| 4 | 1,588 | 78.1% | 0.760495–0.801118 | 1,588 |

### `STRICT` — per-rank calibration by fold

| fold | held-out accepts | rank-1 (HELD-OUT) | 95% CI | n |
|---|---:|---:|---|---:|
| 0 | 720 | 77.1% | 0.738744–0.800048 | 720 |
| 1 | 646 | 69.8% | 0.661656–0.732286 | 646 |
| 2 | 460 | 78.9% | 0.749536–0.823936 | 460 |
| 3 | 303 | 83.2% | 0.785462–0.869599 | 303 |
| 4 | 342 | 73.4% | 0.684674–0.777966 | 342 |

## Ceiling against the same-line bar

What the grid can reach at all, against same-line's 0.90 bar:

| rule | raw top-1 | best rule reaching ≥50 accepts | vs 0.90 target |
|---|---:|---:|---|
| `LAYOUT_AGNOSTIC` | 39.2% | 89.3% on n=1,098 | **short of target** |
| `STRICT` | 31.9% | 89.8% on n=216 | **short of target** |

Same-line spans at this cell reach ~91% at rank 1, which is why 0.90 was a sensible bar for them. Cross-line does not reach it, which is why cross-line has its own ratified target rather than inheriting one. A cross-line rate must always be displayed as a cross-line rate: the populations differ by roughly 5x in gold inclusion, and substituting one for the other is the error this whole line of work exists to prevent.

### What each target would yield — sensitivity, NOT a proposal

The gap between *unreachable* and *reachable at a lower bar* is the decision this raises. These numbers exist so that decision can be made deliberately and recorded, not so a target can be picked because it produced output.

| target | `LAYOUT_AGNOSTIC` | `STRICT` |
|---|---|---|
| 0.70 | 10,050 spans @ 73.1% | 3,821 spans @ 70.7% |
| 0.75 | 8,945 spans @ 75.0% | 3,040 spans @ 76.7% |
| 0.80 | 3,290 spans @ 80.0% | 1,081 spans @ 81.5% |
| 0.85 | 1,847 spans @ 85.7% | 947 spans @ 86.2% |
| 0.90 | unreachable | unreachable |

**Nothing here is adopted.** Lowering a calibration target changes what an expert is told a candidate is worth. That is Ixca's call, and it should be ratified in the open with these numbers in view.

## Does the calibration transfer? (the check that matters)

A selector fit on calibration compositions can look well-calibrated *there* and fail on compositions it has never seen. Fold structure exists to expose that, so it is reported before anything else is believed:

| rule | calibrated rank-1 (promised) | held-out top-1 (delivered) | gap | held-out n |
|---|---:|---:|---:|---:|
| `LAYOUT_AGNOSTIC` | 77.5% | 77.5% | 0.0 pts | 8,208 |
| `STRICT` | 78.1% | 75.8% | 2.3 pts | 2,471 |

**Only the held-out column may be displayed.** The fit-set figure reports how well a selector fit its own calibration compositions, which is not what an expert needs to know. Where the two diverge, the fit-set number is optimistic.

An earlier dev-only run showed a 12.8-point gap on 55 held-out spans, with per-fold accepts of 45/5/1/4 — three of four folds carrying no weight at all. That gap was a small-sample artifact, not a property of cross-line evidence: widening the calibration universe to the governed non-test set closed it. The lesson is kept here because the optimistic reading was available first.

## How to read the abstentions

A fold with *no rule met the calibration target* is a fold where no selector in the grid reached the target agreement with enough calibration accepts. That is reported as-is. The target was not lowered until something passed — a rate obtained that way would describe the search, not the evidence.

## Standing limits

- Adjacent line pairs only (one boundary crossed), matching P2-E8.
- `LAYOUT_AGNOSTIC` is the **ratified** admission rule (2026-07-28 by Ixca); `STRICT` is retained as a declared ablation and is not a fallback.
- Calibration target **0.75** (RATIFIED, 2026-07-28 by Ixca). Same-line keeps 0.90 in its own config; the two must never be pooled or substituted.
- Calibration universe: train+dev, non-bin, test excluded and asserted. Bin documents are unlabeled, not negative, and stay out of every truth set.
- These rates are for cross-line anchors only. P2-E4's same-line rates remain the same-line ones; the two populations differ by roughly 5x in gold inclusion and must never be pooled or substituted.
- Applying these to real gaps is a further step (`real_gap_calibration.py` currently gates on `if not g["is_cross_line"]`), and needs its own review.

Runtime 90.4s · seed 20260728.
