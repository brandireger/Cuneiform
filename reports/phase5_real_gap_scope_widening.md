# Phase 5 successor task — widen real-gap production scope

**Run:** 2026-07-28. Protected-test access, model training, and recalibration
were not involved. P2-E4 and P2-E9 remain separate populations with separate
targets, folds, and attached rates.

## What was wrong

The descriptive witness-check step intentionally uses the top five CTHs by
real-gap count. Production calibration had already moved beyond that slice,
but only partially: `real_gap_calibration.py` passed P2-E4's 38 same-line CTHs
to `prepare_scope()` and then applied P2-E9 inside that prefiltered data.

P2-E9 has usable cross-line folds for 279 CTHs. Restricting the load to the
P2-E4 set silently discarded most of that applicable cross-line scope before
P2-E9 eligibility was checked. This was a scope-composition bug, not a
calibration failure.

## Correction

The script now resolves both typed composition sets before loading content:

| population | applicable CTHs |
|---|---:|
| same-line, P2-E4 | 38 |
| cross-line, P2-E9 | 279 |
| overlap | 29 |
| **union passed to `prepare_scope()`** | **288** |

Each gap still has to belong to its own population's CTH set. If P2-E9 is
missing or its target is unratified, the union fails closed to the P2-E4
same-line set. A regression test pins both behaviors.

## Result

| quantity | before | after |
|---|---:|---:|
| documents loaded | 739 | **6,145** |
| same-line eligible | 703 | **703** |
| same-line accepted | 41 | **41** |
| cross-line eligible | 5,062 | **46,118** |
| cross-line accepted | 61 | **577** |

The unchanged same-line counts are the control: widening the cross-line scope
did not change P2-E4's application population. Cross-line gains 516 accepted
gaps while retaining P2-E9's ratified `LAYOUT_AGNOSTIC` rule, 0.75 target, and
held-out quality claim of 77.5% rank-1 agreement on 8,208 spans with a
0.0-point transfer gap.

These are population-specific counts, not a pooled calibration result.
Cross-line and same-line rates remain non-interchangeable.

## Artifacts

- `scripts/real_gap_calibration.py`
- `tests/test_real_gap_calibration_scope.py`
- `Phase3/real_gaps_out/real_gap_calibration.json`
- `Phase3/real_gaps_out/real_gap_calibration_report.md`

The JSON now records
`UNION_OF_APPLICABLE_SAME_LINE_AND_CROSS_LINE_FOLDS` and preserves the
same-line, cross-line, and union CTH lists separately.

## Validation

- `python -m unittest discover -s tests` — 211 pass.
- Ruff — clean across `lib`, `scripts`, `tests`, and `demo`.
- `lib/contracts.py` — 20/20.
- `scripts/00_tracers.py` — 0 blocking failures; the standing T4 diagnostic
  remains visible and unchanged.
- `scripts/p4d_stamp_stale_reports.py --check` — exit 0.
