# Phase 2 P2-E witness recoverability census

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

- Carried-forward `00_tracers.py`: PASS; 0 blocking failures (its D18 T4 diagnostic remains visible and non-blocking).
- New anchored-witness T1: PASS; synthetic canary passed and 12/12 real canaries changed under token-order scrambling (required 4).

## What was measured

Only frozen **dev** content was read. Restored readings and unreadable `x` placeholders were excluded. For every intentionally masked attested span, an independent same-CTH witness was searched for the same left/right anchors with a variable middle of 0–12 signs. Same-CTH membership selected candidates; it did not count as evidence.

## Primary result (2-sign anchors, 1 hidden sign)

- 70,867 spans were maskable; 68,773 had a structurally available independent witness (97.05%).
- Attested witness evidence existed for 17,390 eligible spans (25.29%). The system abstained on 51,383 (74.71%).
- The hidden attested sign appeared among witness proposals for 14,119 eligible spans (20.53%). 3,271 supported spans supplied only a different/omitted middle; 3,799 supported spans had multiple witness alternatives.
- Composition-macro view (39 eligible CTHs): mean/median support 13.58%/10.01%; mean/median exact agreement 11.24%/6.99%. This guards against large compositions dominating the micro-average.

These are **recoverability and agreement** rates, not accuracy on genuinely lost text. A parallel constrains plausible context but does not prove that two witnesses had identical wording.

## Horizon matrix

| anchors/mask | eligible | supported | exact among eligible | variant-only | ambiguous | abstention |
|---|---:|---:|---:|---:|---:|---:|
| a1_m1 | 94,582 | 68,156 (72.06%) | 44,219 (46.75%) | 23,937 | 51,440 | 27.94% |
| a1_m2 | 81,045 | 55,424 (68.39%) | 24,894 (30.72%) | 30,530 | 42,522 | 31.61% |
| a1_m3 | 68,773 | 45,237 (65.78%) | 14,119 (20.53%) | 31,118 | 35,029 | 34.22% |
| a1_m5 | 48,131 | 29,681 (61.67%) | 4,558 (9.47%) | 25,123 | 22,796 | 38.33% |
| a2_m1 | 68,773 | 17,390 (25.29%) | 14,119 (20.53%) | 3,271 | 3,799 | 74.71% |
| a2_m2 | 57,815 | 11,906 (20.59%) | 8,059 (13.94%) | 3,847 | 3,156 | 79.41% |
| a2_m3 | 48,131 | 8,247 (17.13%) | 4,558 (9.47%) | 3,689 | 2,325 | 82.87% |
| a2_m5 | 32,494 | 4,165 (12.82%) | 1,461 (4.5%) | 2,704 | 1,191 | 87.18% |
| a3_m1 | 48,131 | 5,266 (10.94%) | 4,558 (9.47%) | 708 | 467 | 89.06% |
| a3_m2 | 39,697 | 3,395 (8.55%) | 2,580 (6.5%) | 815 | 377 | 91.45% |
| a3_m3 | 32,494 | 2,253 (6.93%) | 1,461 (4.5%) | 792 | 278 | 93.07% |
| a3_m5 | 21,132 | 1,022 (4.84%) | 483 (2.29%) | 539 | 116 | 95.16% |

## Known-join diagnostic: third-witness textual coverage

182/182 canonical mapped dev join pairs (100.0%) had any independent same-CTH witness. The stricter table requires one witness fragment to contain distinct attested n-grams linked to both join members. 2 raw relation rows were excluded from this denominator because their member IDs did not map to the canonical dev fragment universe.

| shared n-gram length | covered pairs | percent of all dev pairs |
|---:|---:|---:|
| 1 | 177 | 97.25% |
| 2 | 177 | 97.25% |
| 3 | 176 | 96.7% |
| 5 | 128 | 70.33% |

This is a textual-evidence ceiling only. It says nothing about clay fit, edge geometry, or whether A and B are adjacent.

## Decision

Use the horizon matrix as Phase 2's first recoverability map. Any next reconstruction model must emit alternatives and abstain outside the empirically supported cells; join ranking remains a downstream diagnostic, not the project definition.

## Governance

- Evidence profile: `catalog_assisted`.
- Semantic fields: `token`, `damage_state`, `line_index_in_doc`, `cth`; no `cu`, morphology, restorations, editor identity, or model output.
- Test-side content accessed: **no**.
- Seed: 20260723; elapsed: 21.2s.
- Machine-readable result: `Phase2\phase2_out\p2e_witness_recoverability.json`; manifest: `Phase2\phase2_out\p2e_witness_recoverability_manifest.json`.

Corpus: TLHdig Beta 0.2.0, Müller, Prechel, Rieken & Schwemer (2025), DOI 10.5281/zenodo.15459134, CC BY 4.0.
