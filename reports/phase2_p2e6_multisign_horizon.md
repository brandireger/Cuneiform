# Phase 2 P2-E6 multi-sign candidate-set horizon

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
| 2 | 70,933/100,265 (70.75%) | 24.6% | 38.68% [38.3, 39.0] | 27.36% | 6.705 / 16 |
| 3 | 58,745/85,587 (68.64%) | 15.7% | 25.89% [25.5, 26.3] | 17.77% | 7.146 / 18 |
| 4 | 48,736/72,494 (67.23%) | 10.03% | 17.53% [17.2, 17.9] | 11.78% | 7.522 / 19 |
| 5 | 39,988/60,887 (65.68%) | 6.63% | 12.1% [11.8, 12.4] | 7.95% | 7.749 / 19 |

Across fold × mask × selected-anchor groups, the weighted mean absolute calibration-transfer gap was 8.17 percentage points. This is set-level calibration, not an individual option probability.

Composition-macro effective recovery was 16.18% mean / 14.48% median for two signs and 5.32% mean / 2.86% median for five signs; pooled micro rates therefore overstate the typical composition.

## Interpretation

Two-sign sets retained the attested span in 27.36% of eligible contexts; by five signs this fell to 7.95%. Keeping evidence ties complete expanded nominal top-five sets in 33.9% to 38.7% of presented contexts, with p90 up to 19 and a maximum of 237 options. The witness layer is therefore suitable only as abstention-first, set-valued evidence for an expert: do not auto-complete a lacuna, do not assign per-option probabilities, and collapse large equal-support tails in the UI without hiding that they exist.

Cost: 36.4s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, model scores, and generated text untouched.

**Falsifier:** the multi-sign horizon conclusion would be wrong if an untouched composition-disjoint evaluation shows materially different coverage, set inclusion, or option-set size under the same adaptive evidence policy.
