# P2.5 Master Acceptance Report

All 6 acceptance checks from P2.5_AMENDMENTS.md, evaluated against the actual pipeline outputs.

## Check 1 -- cth_bins.csv coverage + human sign-off

- cth_bins.csv covers 657 / 657 corpus CTHs: PASS
- Uncertain entries remaining unresolved: 0 (PASS -- all resolved)
- Sign-off recorded 2026-07-21 (AskUserQuestion in-session): 25 bin-keyword+long-title entries -> BIN (user's explicit choice); 6 seed-mismatch no-keyword entries -> REAL (recommended, no bin evidence). See bins_report.md 'Uncertain list' section and cth_bins.csv `reason` column (`RESOLVED 2026-07-21` suffix) for the full audit trail.
- **CHECK 1: PASS**

## Check 2 -- supervision-eligible corpus + duplicate pairs

- Real (supervision-eligible) compositions: **543**
- Real (supervision-eligible) documents: **7,593**
- Duplicate-positive pairs, naive (all CTHs): **13,451,014**
- Duplicate-positive pairs, bins excluded: **234,263** (98.3% drop)
- **CHECK 2: PASS** -- large drop confirmed and quantified, per spec.

## Check 3 -- discovery pool size

- Discovery pool: **14,046 documents**
- Actual 14,046 vs. the amendment's stated expectation of ~9-10k -- flagged, not silently accepted. The delta traces to the classification threshold (bin keyword + <=6-word title) plus the 25 user-approved 'long/specific fragment title' entries added during sign-off (2026-07-21), both of which pull more compositions into the bin bucket than a size-based guess would.
- **CHECK 3: PASS (stated), with expectation delta flagged as required**

## Check 4 -- join tiers + exclusive-content spot-check

- Tier A: 478, Tier B: 185, Tier C: 918 (487 exclusive_untestable)
- 3-pair exclusive-content spot-check: see `join_tiers_report.md` 'Tier-C exclusive-content spot-check' section
- **CHECK 4: PASS**

## Check 5 -- new split shares, leakage, frozen flag, git commit

- Doc shares: train 80.0% (target 80±3), dev 10.0% (target 10±2), test 10.0% (target 10±2)
- Composition leakage: PASS (0 real compositions span multiple splits)
- Frozen flag: True, date 2026-07-21
- Git commit: `7b010cde8096e1a12b19f9926b72c92b5ae048ac` (real 40-char hash)
- **CHECK 5: PASS**

## Check 6 -- provincial count before/after A5, DAAM evidence

- Provincial-eval documents: 201 (P2) -> 314 (post-A5)
- DAAM evidence: multi-site series confirmed via WebSearch (Rieken 2019 DAAM 1 = Kayalipinar; Schwemer & Suel 2021 DAAM 2 = Ortakoy-Sapinuwa; Bozgun 2025 DAAM 3 + Cilingir Cesur 2025 DAAM 4 = Hattusa museum tablets), applied per volume number, documented in `provenance_patch.md` with citations.
- **CHECK 6: PASS**

## Overall

**ALL 6 CHECKS PASS** -- P2.5 accepted, splits.json frozen 2026-07-21. P3 may proceed on p2_out/splits.parquet's frozen main_split/site_split columns, respecting the bin reframe throughout.