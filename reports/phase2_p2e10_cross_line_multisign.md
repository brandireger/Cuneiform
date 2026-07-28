# Phase 2 P2-E10 — cross-line multi-sign candidate-set calibration

The multi-sign analogue of P2-E9, and the last piece needed before a cross-line real gap longer than one sign can be shown to an expert.

**Estimand is set inclusion, not per-rank agreement.** An expert is shown a set, so the quantity that matters is how often the tie-complete displayed set contains the true span. P2-E9's per-rank rates and these are not interchangeable, in either direction.

Admission rule **LAYOUT_AGNOSTIC** (ratified 2026-07-28 by Ixca); universe train+dev, non-bin, test excluded and asserted; nominal display depth 5.

## Does it transfer?

| mask length | fit-set inclusion | held-out inclusion | gap | held-out n |
|---|---:|---:|---:|---:|
| 2 | 13.8% | 13.8% | +0.0 pts | 235,628 |
| 3 | 10.0% | 10.0% | +0.0 pts | 293,186 |
| 4 | 8.0% | 8.0% | +0.0 pts | 340,887 |
| 5 | 6.7% | 6.7% | +0.0 pts | 377,379 |

**Only the held-out column describes performance on unseen compositions.** As in P2-E9, the rate ATTACHED to a real gap must be the fit-set one for that gap's fold — it is computed on compositions disjoint from the gap's own, whereas the held-out figure is measured on exactly those compositions and would be circular per-gap. The two answer different questions and both are kept.

## Spans no anchor length could support

| mask length | abstained (no witness support at any anchor length) |
|---|---:|
| 2 | 77,020 |
| 3 | 98,359 |
| 4 | 115,806 |
| 5 | 129,921 |

These are not a calibration group and receive no rate. Longer spans abstain more, which is the expected shape: the longer the lost span, the less often an independent witness attests exactly it.

## Conclusion: cross-line multi-sign is not viable for presentation

Set inclusion runs from **13.8%** at two signs down to **6.7%** at five. The
displayed set contains the true span roughly one time in seven at best, and
one time in fifteen at worst. Same-line multi-sign spans are several times
stronger.

The calibration itself is sound -- the fit-set and held-out rates agree to
within 0.0 points on 235,628-377,379 held-out spans, so these numbers are
trustworthy. They are trustworthy evidence that this channel does not work.

**Recommendation: do not wire P2-E10 into
`real_gap_multisign_calibration.py`.** A calibrated 8% set-inclusion rate is
honest but not decision-support: an expert shown such a set would be right to
ignore it, and displaying it would spend their attention for almost no yield.

This bounds where cross-line evidence helps. P2-E9 showed single-sign
cross-line reaching its ratified 0.75 target and it is now applied in
production. Multi-sign cross-line, measured the same way, does not clear a bar
worth setting. Reporting both is the point: the negative result is what stops
the next session from building the application layer this one deliberately
declined to build.

## Standing limits

- Adjacent line pairs only (one boundary crossed), matching P2-E8/E9.
- Cross-line rates are for cross-line gaps. P2-E6's same-line set-inclusion rates stay with same-line gaps; the populations differ and must never be pooled or substituted.
- Set inclusion is a property of the SET, not of any one displayed alternative. There is no per-option probability here.
- Applying these to real gaps is a further step in `real_gap_multisign_calibration.py`, which still reports same-line only.

Runtime 263.5s · seed 20260728.
