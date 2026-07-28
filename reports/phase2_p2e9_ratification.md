# P2-E9 ratification record — cross-line witness admission

**Decided by:** Ixca, 2026-07-28.
**Scope:** one of the two decisions P2-E9 raised. The second is deliberately
still open; see below.

This record does not widen any authorization boundary. Protected-test access
and GPU training remain unauthorized; Gate 3 is untouched.

---

## Decision 1 — `LAYOUT_AGNOSTIC` is the ratified witness-admission rule

**RATIFIED.** A cross-line gap may be answered by any independent witness
occurrence of its anchor pair, including one where the same text sits within a
single line.

**Rationale.** Line division is scribal layout, not textual structure. The
same phrase may be written on one line in one manuscript and across a break in
another, so a same-line witness occurrence is genuine evidence about a
cross-line gap. Refusing it would discard evidence on the basis of a
manuscript's page geometry rather than its content.

**Measured effect** (cell `a2_m1`, dev, `HITTITE_ONLY`):

| quantity | `STRICT` | `LAYOUT_AGNOSTIC` |
|---|---:|---:|
| eligible spans with any support | 6,540 | **8,352** |
| raw top-1 agreement | 24.2% | **32.9%** |
| gold inclusion (P2-E8) | 4.27% | **7.21%** |
| best selector reaching ≥50 accepts | 79.7% (n=64) | **81.2% (n=112)** |

**Implementation.** `configs/p2e9_cross_line_calibration.json` carries the rule
and its status. `STRICT` is **retained as a declared ablation, not deleted** —
adopting a rule should never destroy the comparison that justified it, and a
future reviewer must be able to see what the conservative reading would have
given.

**Support counting.** `LAYOUT_AGNOSTIC` searches two anchor indices, and one
witness family can appear in both. `merged_ranking()` merges family *sets*
before counting, so a family witnessing the same proposal in both indices
counts once. Support is a count of independent sources and is the exact
quantity the selector rule thresholds on; double-counting would inflate the
evidence bar's own input. Pinned by test.

---

## Decision 2 — cross-line calibration target: **0.75, RATIFIED**

**RATIFIED at 0.75** (Ixca, 2026-07-28), from the sensitivity sweep, recorded
before the fold-structured result was known.

Same-line uses 0.90 and clears it at ~91%; cross-line tops out near 81% even
under `LAYOUT_AGNOSTIC`, so 0.90 was unreachable and inheriting it would have
meant permanent abstention dressed as policy. 0.75 widens coverage while
keeping rank-1 agreement well above the weaker alternatives.

`configs/p2e9_cross_line_calibration.json` carries the value, its status, who
ratified it, and why. `require_calibration_target()` refuses a value whose
status is not `RATIFIED`, so a number typed into the config is not by itself a
policy.

### What the ratified target produced, after widening the universe

The first fold-structured run used dev only and looked alarming: a 12.8-point
optimism gap on 55 held-out spans, with per-fold accepts of 45/5/1/4. Three of
four folds carried no weight. Widening the calibration universe to the
governed non-test set (train + dev, non-bin, test excluded and asserted)
resolved it — the gap was a small-sample artifact, not a property of
cross-line evidence.

| universe | held-out accepts | fit-set rank-1 | **held-out rank-1** | gap |
|---|---:|---:|---:|---:|
| dev only | 55 | 81.9% | 69.1% | 12.8 pts |
| **train + dev** | **8,208** | 77.5% | **77.5%** | **0.0 pts** |
| train + dev, `STRICT` (ablation) | 2,471 | 78.1% | 75.8% | 2.3 pts |

**The ratified 0.75 target is met on held-out compositions**: 77.5% delivered
across 279 compositions and all five folds (75.7 / 74.9 / 75.5 / 82.3 / 78.1),
with the calibration transferring exactly.

**`LAYOUT_AGNOSTIC` is vindicated twice over.** It yields 3.3x the held-out
mass of `STRICT` (8,208 vs 2,471) *and* transfers better (0.0 vs 2.3 points).
Retaining `STRICT` as a declared ablation is what makes both claims checkable.

**Widening is leakage-safe for a specific reason**, recorded so no one has to
re-derive it: this calibration consumes no model. It counts independent
witness families in an anchor index, so including train compositions cannot
leak anything a model was fit on. Folds remain composition-level, bin
documents stay out, and test exclusion is asserted via
`contracts.assert_no_test`, not assumed.

### Consumers must display the held-out rate

`rank_calibration_held_out` is the consumer-facing figure and the payload
names it as such. `rank_calibration_calibration_set` is retained only to keep
the transfer gap visible. Showing the fit-set rate would report how well a
selector fit its own calibration compositions, which is not what an expert
needs to know — and on the dev-only run it would have overstated by nearly
thirteen points.

