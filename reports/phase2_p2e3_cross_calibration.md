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
| a1_m1 | 51.82% / 52.88% | 5/5 | 2.73% / 92.26% [91.1, 93.3] | 1/5 |
| a2_m1 | 23.45% / 80.14% | 5/5 | 7.65% / 90.67% [89.8, 91.4] | 2/5 |
| a3_m1 | 10.79% / 84.89% | 5/5 | 2.63% / 90.28% [88.5, 91.8] | 2/5 |



Primary a2_m1 formulaicity: rare (`cth_df_1`) 1.81% coverage / 89.67% agreement; moderate (`cth_df_2_5`) 5.54% / 91.17%; common (`cth_df_6_plus`) 17.27% / 90.66%.
Witness availability: one family 0.0% / —; two–three 0.0% / —; four+ 8.2% / 90.67%.
Composition heterogeneity: 21/38 CTHs received any acceptance; among 15 with ≥20 accepts, median agreement was 93.83% (range 82.61–100.0%).

## Interpretation

The pooled signal is real but does not transfer as a universal reliability threshold. Acceptance is concentrated in recurrent bounded contexts and witness-rich compositions, while per-CTH agreement remains heterogeneous. Those dependencies are reported, not silently treated as universal evidence. This remains masked-attested agreement, not truth for a real lacuna.

Cost: 46.1s compute; budget ≤4h. Profile `catalog_assisted`; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the instability conclusion would be wrong if a future untouched composition-disjoint benchmark retains the selected reliability lower bound consistently across folds and strata.
