# P2.5 A4 -- Resplit Report (FROZEN)

- Seed: 20260721 (new for this re-roll, distinct from P2's 20260720) | Corpus version: TLHdig_0.2.0-beta
- Git commit: `7b010cde8096e1a12b19f9926b72c92b5ae048ac`
- **splits.json is now FROZEN -- this is the LAST re-roll per P2.5_AMENDMENTS.md.**

## Acceptance check -- composition leakage & bin isolation
- Composition leakage: **PASS** (0 of 543 real compositions span multiple splits)
- Bin isolation: **PASS** (0 of 14046 bin documents carry a train/dev/test label; all get `main_split='discovery'`)

## main_split (real compositions only, doc-count-balanced)

| split | documents | doc share | compositions |
|---|---|---|---|
| train | 6073 | 80.0% | 437 |
| dev | 760 | 10.0% | 53 |
| test | 760 | 10.0% | 53 |
| discovery (bins) | 14046 | 64.9% of ALL docs | 114 |

**Compare to P2's original composition-count-only stratified split (05_splits.py): train 71.0% / dev 22.7% / test 6.3% by docs despite balanced composition counts. This greedy doc-count-aware re-roll targets the nominal 80/10/10 directly.**

## site_split (regenerated post-A5 provenance patch)

| bucket | documents |
|---|---|
| train_hattusa | 19228 |
| test_provincial | 314 |
| excluded_unknown_site | 2097 |

- Provincial count: 201 (P2) -> 314 (post-A5 DAAM/Kp verification)

## Size-band / genre-band representation across splits (informational, not a hard constraint on the greedy pass)

| size_band | train | dev | test |
|---|---|---|---|
| 1 | 93 | 11 | 11 |
| 2-5 | 141 | 18 | 18 |
| 21-50 | 55 | 6 | 6 |
| 51+ | 24 | 3 | 3 |
| 6-20 | 124 | 15 | 15 |