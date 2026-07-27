# Phase 2 P2-E2 abstention calibration

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

- `00_tracers.py`: PASS, zero blocking failures; the existing D18 diagnostic remains visible and non-blocking.
- P2-E anchored scorer T1: PASS; 12/12 real canaries changed.
- New evidence-ranker T1: PASS; 12/12 real canaries changed, while candidate-order permutation left the rank unchanged.

## Question

Can independent witness votes identify a subset of missing-context proposals whose reliability is high enough to justify acceptance, while preserving alternatives and abstaining elsewhere?

## What I did

Frozen dev compositions were divided into disjoint calibration (22 CTHs) and evaluation (20 CTHs) sets, balanced by primary-cell eligible spans without reading outcome labels. Alternatives were ranked only by the number of independent witness families supporting them. Evidence ties always abstain. Rules were selected by calibration coverage subject to a lower 95% Wilson reliability bound, then frozen for held-out-composition evaluation.

## What I found — primary cell (two-sign anchors, one hidden sign)

The evidence-only unique-top baseline accepted 22.66% of held-out eligible spans at 82.48% top-1 agreement (calibration: 23.23% coverage, 78.27% agreement).

| calibration lower-bound target | selected rule | calibration coverage / agreement | held-out coverage | held-out agreement [95% CI] |
|---:|---|---:|---:|---:|
| 70% | `s1_m1_d0p0_aany` | 23.23% / 78.27% | 22.66% | 82.48% [81.6, 83.3] |
| 80% | `s2_m1_d0p0_aany` | 10.54% / 84.54% | 7.51% | 90.67% [89.5, 91.7] |
| 90% | `s1_m2_d0p0_a2` | 8.07% / 91.28% | 6.27% | 92.48% [91.3, 93.5] |
| 95% | unattainable | — | — | — |

Across all 12 cells, a calibration rule with a 90% Wilson lower bound existed only for a1_m1, a2_m1, a3_m1; every qualifying cell masked one sign. No two-to-five-sign mask qualified. No cell reached the 95% lower-bound target. In the primary cell, the 90% calibration rule transferred at 92.48% point agreement but a held-out lower bound of 91.3%; the 80% calibration rule transferred at only 90.67%. These thresholds are therefore exploratory selectors, not portable reliability guarantees.

Typed evidence-packet samples preserve accepted alternatives, witness-family support, contradictory variants, enabled assistance layers, and explicit abstention reasons in `Phase2\phase2_out\p2e2_evidence_packets.jsonl`. Full 12-cell frontiers are in the machine-readable result.

## What this rules in / out

It rules in a small, one-sign high-agreement island, but not a stable cross-composition calibration guarantee. It rules out forced completion, lexicographic tie-breaking, and treating catalog co-membership as evidence. This remains agreement against intentionally masked dev text—not proof of a genuinely lost reading.

Cost: 26.6s compute; budget ≤4 hours. Evidence profile `catalog_assisted`; no test content, restorations, `cu`, morphology, or model-generated text.

**Falsifier:** this conclusion would be wrong if the selected rules lose their reliability when evaluated on a future untouched, composition-disjoint masked-attested benchmark.
