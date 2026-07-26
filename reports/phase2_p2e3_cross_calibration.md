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
| a1_m1 | 50.73% / 52.65% | 5/5 | 2.65% / 92.33% [91.2, 93.3] | 3/5 |
| a2_m1 | 22.94% / 80.35% | 5/5 | 8.06% / 88.79% [87.9, 89.6] | 2/5 |
| a3_m1 | 10.51% / 85.2% | 5/5 | 2.6% / 89.6% [87.8, 91.2] | 2/5 |



Primary a2_m1 formulaicity: rare (`cth_df_1`) 1.77% coverage / 89.84% agreement; moderate (`cth_df_2_5`) 5.34% / 90.16%; common (`cth_df_6_plus`) 18.94% / 88.32%.
Witness availability: one family 0.0% / —; two–three 0.29% / 100.0%; four+ 8.94% / 88.76%.
Composition heterogeneity: 22/39 CTHs received any acceptance; among 15 with ≥20 accepts, median agreement was 93.83% (range 82.61–100.0%).

## Interpretation

The pooled signal is real but does not transfer as a universal reliability threshold. Acceptance is concentrated in recurrent bounded contexts and witness-rich compositions, while per-CTH agreement remains heterogeneous. Those dependencies are reported, not silently treated as universal evidence. This remains masked-attested agreement, not truth for a real lacuna.

Cost: 43.4s compute; budget ≤4h. Profile `catalog_assisted`; test, restorations, `cu`, morphology, and model-generated text untouched.

**Falsifier:** the instability conclusion would be wrong if a future untouched composition-disjoint benchmark retains the selected reliability lower bound consistently across folds and strata.
