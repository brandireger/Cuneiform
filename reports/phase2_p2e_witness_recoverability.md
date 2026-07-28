# Phase 2 P2-E witness recoverability census

**[PROBE — not for citation]**

## Tracer block

- Carried-forward `00_tracers.py`: PASS; 0 blocking failures (its D18 T4 diagnostic remains visible and non-blocking).
- New anchored-witness T1: PASS; synthetic canary passed and 12/12 real canaries changed under token-order scrambling (required 4).

## What was measured

Only frozen **dev** content was read. Restored readings and unreadable `x` placeholders were excluded. For every intentionally masked attested span, an independent same-CTH witness was searched for the same left/right anchors with a variable middle of 0–12 signs. Same-CTH membership selected candidates; it did not count as evidence.

## Primary result (2-sign anchors, 1 hidden sign)

- 67,229 spans were maskable; 65,139 had a structurally available independent witness (96.89%).
- Attested witness evidence existed for 16,831 eligible spans (25.84%). The system abstained on 48,308 (74.16%).
- The hidden attested sign appeared among witness proposals for 13,639 eligible spans (20.94%). 3,192 supported spans supplied only a different/omitted middle; 3,662 supported spans had multiple witness alternatives.
- Composition-macro view (38 eligible CTHs): mean/median support 13.84%/10.2%; mean/median exact agreement 11.48%/6.98%. This guards against large compositions dominating the micro-average.

These are **recoverability and agreement** rates, not accuracy on genuinely lost text. A parallel constrains plausible context but does not prove that two witnesses had identical wording.

## Horizon matrix

| anchors/mask | eligible | supported | exact among eligible | variant-only | ambiguous | abstention |
|---|---:|---:|---:|---:|---:|---:|
| a1_m1 | 89,899 | 66,284 (73.73%) | 42,924 (47.75%) | 23,360 | 50,008 | 26.27% |
| a1_m2 | 76,906 | 53,920 (70.11%) | 24,097 (31.33%) | 29,823 | 41,289 | 29.89% |
| a1_m3 | 65,139 | 43,997 (67.54%) | 13,639 (20.94%) | 30,358 | 34,026 | 32.46% |
| a1_m5 | 45,352 | 28,886 (63.69%) | 4,400 (9.7%) | 24,486 | 22,145 | 36.31% |
| a2_m1 | 65,139 | 16,831 (25.84%) | 13,639 (20.94%) | 3,192 | 3,662 | 74.16% |
| a2_m2 | 54,626 | 11,518 (21.09%) | 7,781 (14.24%) | 3,737 | 3,051 | 78.91% |
| a2_m3 | 45,352 | 7,984 (17.6%) | 4,400 (9.7%) | 3,584 | 2,249 | 82.4% |
| a2_m5 | 30,400 | 4,019 (13.22%) | 1,403 (4.62%) | 2,616 | 1,147 | 86.78% |
| a3_m1 | 45,352 | 5,100 (11.25%) | 4,400 (9.7%) | 700 | 462 | 88.75% |
| a3_m2 | 37,284 | 3,297 (8.84%) | 2,487 (6.67%) | 810 | 372 | 91.16% |
| a3_m3 | 30,400 | 2,189 (7.2%) | 1,403 (4.62%) | 786 | 278 | 92.8% |
| a3_m5 | 19,563 | 980 (5.01%) | 450 (2.3%) | 530 | 116 | 94.99% |

## Known-join diagnostic: third-witness textual coverage

182/182 canonical mapped dev join pairs (100.0%) had any independent same-CTH witness. The stricter table requires one witness fragment to contain distinct attested n-grams linked to both join members. 2 raw relation rows were excluded from this denominator because their member IDs did not map to the canonical dev fragment universe.

| shared n-gram length | covered pairs | percent of all dev pairs |
|---:|---:|---:|
| 1 | 175 | 96.15% |
| 2 | 175 | 96.15% |
| 3 | 174 | 95.6% |
| 5 | 127 | 69.78% |

This is a textual-evidence ceiling only. It says nothing about clay fit, edge geometry, or whether A and B are adjacent.

## Decision

Use the horizon matrix as Phase 2's first recoverability map. Any next reconstruction model must emit alternatives and abstain outside the empirically supported cells; join ranking remains a downstream diagnostic, not the project definition.

## Governance

- Evidence profile: `catalog_assisted`.
- Semantic fields: `token`, `damage_state`, `line_index_in_doc`, `cth`; no `cu`, morphology, restorations, editor identity, or model output.
- Test-side content accessed: **no**.
- Seed: 20260723; elapsed: 24.0s.
- Machine-readable result: `Phase2\phase2_out\p2e_witness_recoverability.json`; manifest: `Phase2\phase2_out\p2e_witness_recoverability_manifest.json`.

Corpus: TLHdig Beta 0.2.0, Müller, Prechel, Rieken & Schwemer (2025), DOI 10.5281/zenodo.15459134, CC BY 4.0.
