# Phase 2 P2-E5 observed-context alignment diagnostic

**[PROBE — not for citation]**

## Tracer block

- Base tracers: PASS, zero blocking failures; historical D18 T4 remains diagnostic and non-blocking.
- Existing witness-ranker/formulaicity controls: PASS.
- New alignment T1: PASS; 12/12 real canaries changed under token-order scrambling, and witness-line order was invariant.

## Question and method

For Q0/Q3, can observed-context alignment recover a compact option set for the P2-E4 cases where the hidden attested sign was absent from every exact-anchor alternative? This is a post-hoc residual diagnostic, not a deployable selector. Retrieval required observed bigram evidence on both sides; two flanks were aligned monotonically around a bounded 0–12-sign witness middle. The hidden sign was used only after ranking.

## Findings

231/353 contexts produced any alignment candidate (65.44%).

| displayed alignment depth | mean added options / residual context | exact rescue | 95% Wilson CI |
|---:|---:|---:|---:|
| 1 | 0.654 | 2/353 (0.57%) | [0.2, 2.0] |
| 2 | 0.813 | 5/353 (1.42%) | [0.6, 3.3] |
| 3 | 0.856 | 5/353 (1.42%) | [0.6, 3.3] |
| 5 | 0.892 | 5/353 (1.42%) | [0.6, 3.3] |

At depth five, composition-macro rescue across 19 CTHs had mean 0.24% and median 0.0% (range 0.0–2.56%).
Even an impossible oracle that applied alignment only to known exact-anchor absences would move selected-context full-set inclusion from 92.92% to 93.02% (+0.1 percentage points).

| prior exact-anchor disagreement | contexts | exact rescue @5 |
|---|---:|---:|
| `ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT` | 59 | 1 (1.69%) |
| `ATTESTED_READING_ABSENT_TOP_LONGER` | 158 | 2 (1.27%) |
| `ATTESTED_READING_ABSENT_TOP_OMISSION` | 136 | 2 (1.47%) |

Every packet persists aligned query/witness rows, gaps, boundaries, source families, and contradictions. Alignment scores are explicitly uncalibrated and are not displayed as probabilities.

## Interpretation

Alignment recovered only 5/353 post-hoc residuals while adding candidates to many more contexts; even the residual-only oracle ceiling is +0.1 percentage points. This exploratory yield does not justify integrating or calibrating the alignment layer. Preserve exact-anchor candidate sets and abstention; next map set-valued utility across multi-sign spans, which the intended expert UI must also support.

Cost: 35.4s compute; budget ≤4h. Profile `discovery_assisted`; dev-only residual diagnostic; test, restorations, `cu`, morphology, and generated text untouched.

**Falsifier:** the conclusion that this alignment layer is not worth integrating would be wrong if a non-residual composition-disjoint evaluation selected without hidden labels yields a materially larger attested-span gain at comparable set size and constraints.
