# Phase 2 P2-E4 expert candidate-set audit

**[PROBE — not for citation]**

## Tracer block

- Base tracers: PASS, zero blocking failures; historical D18 T4 remains diagnostic and non-blocking.
- Reused anchored scorer/ranker and formulaicity T1: PASS.
- Candidate-set tracer: PASS; a synthetic rank-2 attested reading missed top-1 and was retained at top-2.

## Question and method

For Q0/Q3, does a compact ranked option set retain intentionally hidden attested text when top-1 differs, and what observable conditions characterize remaining disagreements? The primary two-anchor/one-sign P2-E3 records were reused under the same five composition-disjoint 90%-target selectors. No category below adjudicates a variant, error, or restoration.

## Findings

Across all 21,069 witness-supported contexts, the full preserved set included the hidden attested reading in 78.77%; median set size was 1 and p90 was 2. The fold selectors presented 5,486 contexts (6.41% of all eligible spans).

| displayed depth | mean options shown | attested inclusion | 95% Wilson CI |
|---:|---:|---:|---:|
| 1 | 1 | 4,936/5,486 (89.97%) | [89.2, 90.7] |
| 2 | 1.264 | 5,079/5,486 (92.58%) | [91.9, 93.2] |
| 3 | 1.322 | 5,099/5,486 (92.95%) | [92.2, 93.6] |
| 5 | 1.339 | 5,099/5,486 (92.95%) | [92.2, 93.6] |

The complete preserved set included the attested reading in 5,099/5,486 (92.95%). Thus 163 top-1 misses were recoverable by showing alternatives; 387 were absent from all independent-witness middles.
Across the 24 CTHs with presented contexts, full-set composition-macro inclusion had mean 83.11% and median 93.12% (range 0.0–100.0%), so the pooled result is not a uniform composition-level guarantee.

| observable category among top-1 disagreements | contexts | share |
|---|---:|---:|
| `ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT` | 69 | 12.55% |
| `ATTESTED_READING_ABSENT_TOP_LONGER` | 158 | 28.73% |
| `ATTESTED_READING_ABSENT_TOP_OMISSION` | 160 | 29.09% |
| `ATTESTED_READING_LOWER_RANKED` | 163 | 29.64% |

Nonexclusive flags: 79.27% used anchors recurring across multiple CTHs, and 26.55% repeated the same anchors within the query fragment.

Rank-conditioned calibration estimates with `n` and Wilson CIs are saved in every sampled packet. They are coarse group estimates from other compositions, not instance-level truth probabilities.

## Interpretation

The candidate-set formulation recovers some information hidden by top-1 exact match, but it does not turn every disagreement into a valid restoration. Cases where the attested middle is absent need alignment/variant-aware investigation or abstention; the typed packets preserve that distinction for expert review.

Cost: 32.4s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the candidate-set benefit would be wrong if an untouched composition-disjoint evaluation shows that additional displayed alternatives do not increase attested-span inclusion beyond top-1 at a comparably small set size.
