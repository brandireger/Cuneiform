# Phase 2 P2-E witness recoverability census

**[PROBE — not for citation]**

## Tracer block

- Carried-forward `00_tracers.py`: PASS; 0 blocking failures (its D18 T4 diagnostic remains visible and non-blocking).
- New anchored-witness T1: PASS; synthetic canary passed and 12/12 real canaries changed under token-order scrambling (required 4).

## What was measured

Only frozen **dev** content was read. Restored readings and unreadable `x` placeholders were excluded. For every intentionally masked attested span, an independent same-CTH witness was searched for the same left/right anchors with a variable middle of 0–12 signs. Same-CTH membership selected candidates; it did not count as evidence.

## Primary result (2-sign anchors, 1 hidden sign)

- 88,929 spans were maskable; 85,587 had a structurally available independent witness (96.24%).
- Attested witness evidence existed for 21,069 eligible spans (24.62%). The system abstained on 64,518 (75.38%).
- The hidden attested sign appeared among witness proposals for 16,597 eligible spans (19.39%). 4,472 supported spans supplied only a different/omitted middle; 5,179 supported spans had multiple witness alternatives.
- Composition-macro view (42 eligible CTHs): mean/median support 13.68%/10.92%; mean/median exact agreement 11.29%/9.54%. This guards against large compositions dominating the micro-average.

These are **recoverability and agreement** rates, not accuracy on genuinely lost text. A parallel constrains plausible context but does not prove that two witnesses had identical wording.

## Horizon matrix

| anchors/mask | eligible | supported | exact among eligible | variant-only | ambiguous | abstention |
|---|---:|---:|---:|---:|---:|---:|
| a1_m1 | 116,426 | 85,762 (73.66%) | 53,411 (45.88%) | 32,351 | 67,554 | 26.34% |
| a1_m2 | 100,265 | 70,933 (70.75%) | 29,341 (29.26%) | 41,592 | 56,751 | 29.25% |
| a1_m3 | 85,587 | 58,745 (68.64%) | 16,597 (19.39%) | 42,148 | 47,476 | 31.36% |
| a1_m5 | 60,887 | 39,988 (65.68%) | 5,383 (8.84%) | 34,605 | 32,328 | 34.32% |
| a2_m1 | 85,587 | 21,069 (24.62%) | 16,597 (19.39%) | 4,472 | 5,179 | 75.38% |
| a2_m2 | 72,494 | 14,684 (20.26%) | 9,469 (13.06%) | 5,215 | 4,401 | 79.74% |
| a2_m3 | 60,887 | 10,465 (17.19%) | 5,383 (8.84%) | 5,082 | 3,298 | 82.81% |
| a2_m5 | 42,033 | 5,566 (13.24%) | 1,716 (4.08%) | 3,850 | 1,854 | 86.76% |
| a3_m1 | 60,887 | 6,279 (10.31%) | 5,383 (8.84%) | 896 | 636 | 89.69% |
| a3_m2 | 50,740 | 4,111 (8.1%) | 3,056 (6.02%) | 1,055 | 519 | 91.9% |
| a3_m3 | 42,033 | 2,752 (6.55%) | 1,716 (4.08%) | 1,036 | 399 | 93.45% |
| a3_m5 | 28,120 | 1,269 (4.51%) | 555 (1.97%) | 714 | 185 | 95.49% |

## Known-join diagnostic: third-witness textual coverage

182/182 canonical mapped dev join pairs (100.0%) had any independent same-CTH witness. The stricter table requires one witness fragment to contain distinct attested n-grams linked to both join members. 2 raw relation rows were excluded from this denominator because their member IDs did not map to the canonical dev fragment universe.

| shared n-gram length | covered pairs | percent of all dev pairs |
|---:|---:|---:|
| 1 | 182 | 100.0% |
| 2 | 182 | 100.0% |
| 3 | 181 | 99.45% |
| 5 | 130 | 71.43% |

This is a textual-evidence ceiling only. It says nothing about clay fit, edge geometry, or whether A and B are adjacent.

## Decision

Use the horizon matrix as Phase 2's first recoverability map. Any next reconstruction model must emit alternatives and abstain outside the empirically supported cells; join ranking remains a downstream diagnostic, not the project definition.

## Governance

- Evidence profile: `catalog_assisted`.
- Semantic fields: `token`, `damage_state`, `line_index_in_doc`, `cth`; no `cu`, morphology, restorations, editor identity, or model output.
- Test-side content accessed: **no**.
- Seed: 20260723; elapsed: 23.5s.
- Machine-readable result: `phase2_out\p2e_witness_recoverability.json`; manifest: `phase2_out\p2e_witness_recoverability_manifest.json`.

Corpus: TLHdig Beta 0.2.0, Müller, Prechel, Rieken & Schwemer (2025), DOI 10.5281/zenodo.15459134, CC BY 4.0.
