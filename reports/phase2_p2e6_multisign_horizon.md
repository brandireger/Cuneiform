# Phase 2 P2-E6 multi-sign candidate-set horizon

<!-- p4d-staleness-stamp -->
> **[PREDATES P4-D — numbers not recomputed]** This report was produced under
> the pre-Phase-4 line-granularity Hittite filter. P4-D (2026-07-26) replaced
> it with a required, word-aware language scope
> (`reports/phase4_p4d_language_aware_apis.md`). On the measured real-gap
> slice the word-aware projection refuses **932 lines** the line-granularity
> filter admitted — `Hit`-tagged lines carrying explicit non-Hittite words —
> reducing witness-index tokens by ~6.1%. The direction of the effect on this
> report's figures is therefore known but its magnitude is not; the numbers
> below have **not** been recomputed. Rerunning is P4-G work.

**[PROBE — not for citation]**

## Tracer block

- Base tracers: PASS, zero blocking failures; historical D18 T4 remains diagnostic and non-blocking.
- Witness ranker T1: PASS; 12/12 real canaries changed under token order scrambling and candidate ordering was invariant.
- Adaptive policy tracer: PASS; equal-support alternatives at the display boundary were retained together.

## Question and method

For Q0, what set-valued evidence remains for two-to-five-sign gaps? For each dev span, the policy selected the longest supported exact anchor (3→2→1), presented nominally five alternatives while keeping boundary ties complete, and otherwise abstained. Hidden attested text never affected anchor selection or ranking. Set-level calibration in packets was fit on other composition folds.

## Findings

| hidden span | presented / eligible | top-1 agreement | displayed-set inclusion among presented [95% CI] | effective inclusion / eligible | mean / p90 options |
|---:|---:|---:|---:|---:|---:|
| 2 | 55,424/81,045 (68.39%) | 27.95% | 42.56% [42.2, 43.0] | 29.11% | 4.891 / 12 |
| 3 | 45,237/68,773 (65.78%) | 17.97% | 29.0% [28.6, 29.4] | 19.07% | 5.104 / 12 |
| 4 | 36,878/57,815 (63.79%) | 11.75% | 20.02% [19.6, 20.4] | 12.77% | 5.291 / 13 |
| 5 | 29,681/48,131 (61.67%) | 8.01% | 14.1% [13.7, 14.5] | 8.69% | 5.406 / 13 |

Across fold × mask × selected-anchor groups, the weighted mean absolute calibration-transfer gap was 6.64 percentage points. This is set-level calibration, not an individual option probability.

Composition-macro effective recovery was 16.3% mean / 13.09% median for two signs and 5.41% mean / 2.38% median for five signs; pooled micro rates therefore overstate the typical composition.

## Interpretation

Two-sign sets retained the attested span in 29.11% of eligible contexts; by five signs this fell to 8.69%. Keeping evidence ties complete expanded nominal top-five sets in 27.4% to 31.1% of presented contexts, with p90 up to 13 and a maximum of 85 options. The witness layer is therefore suitable only as abstention-first, set-valued evidence for an expert: do not auto-complete a lacuna, do not assign per-option probabilities, and collapse large equal-support tails in the UI without hiding that they exist.

Cost: 28.7s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, model scores, and generated text untouched.

**Falsifier:** the multi-sign horizon conclusion would be wrong if an untouched composition-disjoint evaluation shows materially different coverage, set inclusion, or option-set size under the same adaptive evidence policy.
