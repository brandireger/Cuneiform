# Phase 2 P2-E3 five-fold cross-calibration

**[PROBE — not for citation]**

## Tracer block

- Base tracers: PASS, zero blocking failures; D18's historical diagnostic remains visible and non-blocking.
- Anchored scorer and witness-ranker T1: PASS, 12/12 real canaries changed under token-order scrambling; candidate-order invariant.
- Formulaicity T1: PASS; scrambling changed the synthetic cross-CTH anchored-context frequency.

## Question and method

Do abstention rules transfer across compositions when every eligible dev CTH is held out once? Five CTH-disjoint folds were balanced by eligible spans. Rules were recalibrated on four folds and frozen for the fifth. Formulaicity was fit over the declared real-composition train+dev universe and used only for analysis.

## Findings

| cell | unique-top baseline coverage / agreement | folds with 90% calibration rule | pooled 90%-selector coverage / agreement [95% CI] | held-out folds retaining 90% lower bound |
|---|---:|---:|---:|---:|
| a1_m1 | 51.08% / 48.27% | 4/5 | 1.2% / 90.72% [89.1, 92.1] | 1/5 |
| a2_m1 | 21.87% / 78.21% | 5/5 | 6.41% / 89.97% [89.2, 90.7] | 1/5 |
| a3_m1 | 9.77% / 84.37% | 5/5 | 1.96% / 89.2% [87.3, 90.8] | 1/5 |

No 95% calibration rule was available in any cell or fold.

Primary a2_m1 formulaicity: rare (`cth_df_1`) 2.0% coverage / 85.98% agreement; moderate (`cth_df_2_5`) 4.9% / 92.77%; common (`cth_df_6_plus`) 16.01% / 90.02%.
Witness availability: one family 0.0% / —; two–three 0.27% / 100.0%; four+ 7.17% / 89.95%.
Composition heterogeneity: 24/42 CTHs received any acceptance; among 16 with ≥20 accepts, median agreement was 94.72% (range 73.53–100.0%).

## Interpretation

The pooled signal is real but does not transfer as a universal reliability threshold. Acceptance is concentrated in recurrent bounded contexts and witness-rich compositions, while per-CTH agreement remains heterogeneous. Those dependencies are reported, not silently treated as universal evidence. This remains masked-attested agreement, not truth for a real lacuna.

Cost: 46.2s compute; budget ≤4h. Profile `catalog_assisted`; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the instability conclusion would be wrong if a future untouched composition-disjoint benchmark retains the selected reliability lower bound consistently across folds and strata.
