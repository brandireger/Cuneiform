# Phase 2 P2-E4 expert candidate-set audit

**[PROBE — not for citation]**

## Tracer block

- Base tracers: PASS, zero blocking failures; historical D18 T4 remains diagnostic and non-blocking.
- Reused anchored scorer/ranker and formulaicity T1: PASS.
- Candidate-set tracer: PASS; a synthetic rank-2 attested reading missed top-1 and was retained at top-2.

## Question and method

For Q0/Q3, does a compact ranked option set retain intentionally hidden attested text when top-1 differs, and what observable conditions characterize remaining disagreements? The primary two-anchor/one-sign P2-E3 records were reused under the same five composition-disjoint 90%-target selectors. No category below adjudicates a variant, error, or restoration.

## Findings

Across all 16,831 witness-supported contexts, the full preserved set included the hidden attested reading in 81.03%; median set size was 1 and p90 was 2. The fold selectors presented 4,983 contexts (7.65% of all eligible spans).

| displayed depth | mean options shown | attested inclusion | 95% Wilson CI |
|---:|---:|---:|---:|
| 1 | 1 | 4,518/4,983 (90.67%) | [89.8, 91.4] |
| 2 | 1.224 | 4,630/4,983 (92.92%) | [92.2, 93.6] |
| 3 | 1.227 | 4,630/4,983 (92.92%) | [92.2, 93.6] |
| 5 | 1.227 | 4,630/4,983 (92.92%) | [92.2, 93.6] |

The complete preserved set included the attested reading in 4,630/4,983 (92.92%). Thus 112 top-1 misses were recoverable by showing alternatives; 353 were absent from all independent-witness middles.
Across the 21 CTHs with presented contexts, full-set composition-macro inclusion had mean 82.09% and median 92.94% (range 0.0–100.0%), so the pooled result is not a uniform composition-level guarantee.

| observable category among top-1 disagreements | contexts | share |
|---|---:|---:|
| `ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT` | 59 | 12.69% |
| `ATTESTED_READING_ABSENT_TOP_LONGER` | 158 | 33.98% |
| `ATTESTED_READING_ABSENT_TOP_OMISSION` | 136 | 29.25% |
| `ATTESTED_READING_LOWER_RANKED` | 112 | 24.09% |

Nonexclusive flags: 89.25% used anchors recurring across multiple CTHs, and 20.0% repeated the same anchors within the query fragment.

Rank-conditioned calibration estimates with `n` and Wilson CIs are saved in every sampled packet. They are coarse group estimates from other compositions, not instance-level truth probabilities.

## Interpretation

The candidate-set formulation recovers some information hidden by top-1 exact match, but it does not turn every disagreement into a valid restoration. Cases where the attested middle is absent need alignment/variant-aware investigation or abstention; the typed packets preserve that distinction for expert review.

Cost: 34.8s compute; budget ≤4h. Profile `catalog_assisted`; dev only; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the candidate-set benefit would be wrong if an untouched composition-disjoint evaluation shows that additional displayed alternatives do not increase attested-span inclusion beyond top-1 at a comparably small set size.
