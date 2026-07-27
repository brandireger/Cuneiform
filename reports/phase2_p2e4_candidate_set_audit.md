# Phase 2 P2-E4 expert candidate-set audit

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
- Reused anchored scorer/ranker and formulaicity T1: PASS.
- Candidate-set tracer: PASS; a synthetic rank-2 attested reading missed top-1 and was retained at top-2.

## Question and method

For Q0/Q3, does a compact ranked option set retain intentionally hidden attested text when top-1 differs, and what observable conditions characterize remaining disagreements? The primary two-anchor/one-sign P2-E3 records were reused under the same five composition-disjoint 90%-target selectors. No category below adjudicates a variant, error, or restoration.

## Findings

Across all 17,390 witness-supported contexts, the full preserved set included the hidden attested reading in 81.19%; median set size was 1.0 and p90 was 2. The fold selectors presented 5,542 contexts (8.06% of all eligible spans).

| displayed depth | mean options shown | attested inclusion | 95% Wilson CI |
|---:|---:|---:|---:|
| 1 | 1 | 4,921/5,542 (88.79%) | [87.9, 89.6] |
| 2 | 1.275 | 5,104/5,542 (92.1%) | [91.4, 92.8] |
| 3 | 1.344 | 5,136/5,542 (92.67%) | [92.0, 93.3] |
| 5 | 1.358 | 5,136/5,542 (92.67%) | [92.0, 93.3] |

The complete preserved set included the attested reading in 5,136/5,542 (92.67%). Thus 215 top-1 misses were recoverable by showing alternatives; 406 were absent from all independent-witness middles.
Across the 22 CTHs with presented contexts, full-set composition-macro inclusion had mean 82.76% and median 93.28% (range 0.0–100.0%), so the pooled result is not a uniform composition-level guarantee.

| observable category among top-1 disagreements | contexts | share |
|---|---:|---:|
| `ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT` | 67 | 10.79% |
| `ATTESTED_READING_ABSENT_TOP_LONGER` | 186 | 29.95% |
| `ATTESTED_READING_ABSENT_TOP_OMISSION` | 153 | 24.64% |
| `ATTESTED_READING_LOWER_RANKED` | 215 | 34.62% |

Nonexclusive flags: 91.79% used anchors recurring across multiple CTHs, and 23.03% repeated the same anchors within the query fragment.

Rank-conditioned calibration estimates with `n` and Wilson CIs are saved in every sampled packet. They are coarse group estimates from other compositions, not instance-level truth probabilities.

## Interpretation

The candidate-set formulation recovers some information hidden by top-1 exact match, but it does not turn every disagreement into a valid restoration. Cases where the attested middle is absent need alignment/variant-aware investigation or abstention; the typed packets preserve that distinction for expert review.

Cost: 32.9s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the candidate-set benefit would be wrong if an untouched composition-disjoint evaluation shows that additional displayed alternatives do not increase attested-span inclusion beyond top-1 at a comparably small set size.
