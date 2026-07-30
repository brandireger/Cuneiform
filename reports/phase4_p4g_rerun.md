# Phase 4 P4-G — downstream rerun under the P4-D language projection

**Run:** 2026-07-27. All ten affected artifacts recomputed under the required,
word-aware `HITTITE_ONLY` scope. Nine reports no longer carry a
`[PREDATES P4-D]` stamp because they are no longer stale; the tenth keeps its
note for a different reason, below.

This closes ratification decision 5, whose deadline was "before any P7 paper
drafting." Protected-test material was not opened, no training artifact
changed, and Gate 3 remains closed.

## What was rerun

| script | wall time |
|---|---|
| `p2e_witness_recoverability.py` | 25 s |
| `p2e2_abstention_calibration.py` | 30 s |
| `p2e3_cross_calibration.py` | 48 s |
| `p2e4_candidate_set_audit.py` | 36 s |
| `p2e5_alignment_probe.py` | 37 s |
| `p2e6_multisign_horizon.py` | 31 s |
| `p2e7_contract_check.py` | 1 s |
| `real_gap_census.py` | 58 s |
| `real_gap_witness_check.py` | 13 s |
| `real_gap_calibration.py` | 11 s |
| `real_gap_multisign_calibration.py` | 11 s |

Under five minutes in total. The deferral was never about cost; it was about
not recomputing numbers in the same session that changed what they mean.

## The headline: contamination was *depressing* the coverage rates

The witness side loses ~5% of its eligible spans, and the coverage rate on
what remains goes **up**. The removed material was largely spans that could
not be answered anyway — non-Hittite content sitting in a Hittite-only index.

| P2-E cell | eligible before → after | with witness support before → after |
|---|---|---|
| `a1_m1` | 94,582 → **89,899** | 72.06% → **73.73%** |
| `a1_m2` | 81,045 → **76,906** | 68.39% → **70.11%** |
| `a1_m3` | 68,773 → **65,139** | 65.78% → **67.54%** |
| `a2_m1` | 68,773 → **65,139** | 25.29% → **25.84%** |

P2-E4 candidate sets move the same way: 17,390 → 16,831 witness-supported
contexts, set-inclusion 81.19% → **81.03%**, selector-presented 5,542 (8.06%)
→ **4,983 (7.65%)**.

This is the honest version of a result that was previously slightly wrong in
both directions at once — a denominator inflated with material the index could
never serve, and a rate diluted by it.

## The query side is now visible, and it matches the P4-D estimate

P4-D predicted ~9.5% of the real-gap query denominator was non-Hittite or
unresolved. Measured on rerun, with every exclusion typed rather than counted
in bulk:

| slice | gaps excluded by `HITTITE_ONLY` | reasons |
|---|---:|---|
| witness check | 2,435 of 25,559 (9.5%) | 1,216 `OUT_OF_SCOPE_LANGUAGE`, 943 `MIXED_LANGUAGE_LINE`, 275 `LINE_NOT_IN_LANGUAGE_DATASET`, 1 `UNRESOLVED_LEXICAL_LANGUAGE` |
| single-sign calibration | 4,061 of 21,536 | 3,391 / 569 / 101 |
| multi-sign calibration | 1,436 of 8,900 | 1,146 / 243 / 47 |

A gap may now only *ask* under the same explicit scope that governs which
witness lines may *answer*.

## The calibrated-coverage funnel, corrected

| stage | before | after |
|---|---:|---:|
| Corpus real-gap runs | 181,051 | **181,051** (unchanged) |
| In scope (top-5 CTHs, language-resolved) | 25,559 | **23,124** |
| With a full 2-sign anchor | 19,339 | **17,240** |
| — same-line (calibration exists) | 1,960 | **1,741** |
| — cross-line (**no calibration exists**) | 17,379 | **15,499** |
| Single-sign selector-accepted | 46 | **41** |
| Multi-sign presented / abstained | 923 / 394 | **798 / 262** |
| **Presented with a calibrated quantity** | 969 (0.54%) | **839 (0.46%)** |

Cross-line remains **89.9%** of anchored gaps and remains entirely
uncalibrated. The rerun did not change that ratio; it confirmed it on clean
numbers. A cross-line calibration pass is still the highest-leverage backend
item available.

## One caveat was removed that should not have been

Regenerating `real_gap_census_report.md` stripped its note — and the note was
still true. The census is a deliberately language-blind structural count; its
181,051 runs are unchanged and it still emits no language keys. Its stamp was
never a staleness claim, it was a scope disclosure.

The CI guard wired in the same session caught this immediately
(`p4d_stamp_stale_reports.py --check` returned exit 1). The census was
re-stamped and stays in `TARGETS` until the census itself is
language-stratified; the nine genuinely-rerun reports moved to
`RERUN_UNDER_P4D`, which `--check` now verifies are *not* stamped. The
invariant is two-sided: a stale report cannot lose its warning, and a current
report cannot keep one.

That this fired on its author's own change, within minutes of being wired in,
is the argument for having wired it in.

## Validation

- 182 unit tests pass; Ruff clean; `lib/contracts.py` 20/20.
- `p4d_stamp_stale_reports.py --check` exits 0; exactly one stamp remains in
  the tree, on the census, by design.
- Every rerun script re-ran its own C1 encoding assertion (`unk_rate=0.0009`
  on 153,821 tokens) — the E2 guard, live on each pass.

## What this does not change

> **Later-status note (2026-07-30):** The bullets below record what remained
> true at the close of P4-G on 2026-07-27. P2-E9 subsequently calibrated and
> activated cross-line single-sign evidence, and the production scope was
> widened; P2-E10 measured cross-line multi-sign evidence and deliberately did
> not apply it. See `PHASE5_SUCCESSOR_HANDOFF.md`.

- Cross-line anchors are still uncalibrated. Descriptive coverage only.
- Calibration still covers 5 CTHs of 543 real compositions.
- The tokenizer vocabulary is still the language-blind Phase 1 one; that is
  entangled with the frozen D14 checkpoint and belongs to P4-F.
- P7 drafting is now unblocked on *these* numbers, but the 0.46% figure is the
  honest headline until cross-line calibration exists.
