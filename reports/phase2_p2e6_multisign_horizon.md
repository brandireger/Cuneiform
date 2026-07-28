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
| 2 | 53,920/76,906 (70.11%) | 27.96% | 42.36% [41.9, 42.8] | 29.7% | 4.853 / 12 |
| 3 | 43,997/65,139 (67.54%) | 17.94% | 28.92% [28.5, 29.3] | 19.53% | 5.082 / 12 |
| 4 | 35,892/54,626 (65.7%) | 11.74% | 19.94% [19.5, 20.4] | 13.1% | 5.272 / 13 |
| 5 | 28,886/45,352 (63.69%) | 7.99% | 14.03% [13.6, 14.4] | 8.94% | 5.387 / 13 |

Across fold × mask × selected-anchor groups, the weighted mean absolute calibration-transfer gap was 5.67 percentage points. This is set-level calibration, not an individual option probability.

Composition-macro effective recovery was 16.08% mean / 13.15% median for two signs and 5.56% mean / 2.86% median for five signs; pooled micro rates therefore overstate the typical composition.

## Interpretation

Two-sign sets retained the attested span in 29.7% of eligible contexts; by five signs this fell to 8.94%. Keeping evidence ties complete expanded nominal top-five sets in 27.5% to 31.2% of presented contexts, with p90 up to 13 and a maximum of 85 options. The witness layer is therefore suitable only as abstention-first, set-valued evidence for an expert: do not auto-complete a lacuna, do not assign per-option probabilities, and collapse large equal-support tails in the UI without hiding that they exist.

Cost: 29.7s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, model scores, and generated text untouched.

**Falsifier:** the multi-sign horizon conclusion would be wrong if an untouched composition-disjoint evaluation shows materially different coverage, set inclusion, or option-set size under the same adaptive evidence policy.
