# P2 Deliverable 4 -- Splits Report

- Seed: 20260720 | Corpus version: TLHdig_0.2.0-beta | Git commit: N/A (not a git repository)
- Compositions (CTH) split: 657
- Documents split: 21639

## Acceptance check #4 -- composition leakage
**PASS (0 compositions span multiple splits)** (programmatically asserted; 0 leaking compositions found)

## main_split (train/dev/test, composition-disjoint)

| split | documents | doc share | compositions |
|---|---|---|---|
| train | 15358 | 71.0% | 518 |
| dev | 4919 | 22.7% | 70 |
| test | 1362 | 6.3% | 69 |

**Caveat: document-count shares deviate from the nominal 80/10/10 target** (stratification balances *composition* count per (size_band, genre_band) stratum, not document count) -- composition size is heavy-tailed (65 compositions have 51+ docs, some far more), so which large compositions land in dev vs test by chance swings doc-count share noticeably even with matched composition counts. This is a known, documented consequence of composition-level splitting being required for leakage safety, not a bug -- report doc counts per split alongside any dev/test metric rather than assuming parity.

## site_split (Hattusa -> provincial generalization axis)

| bucket | documents |
|---|---|
| train_hattusa | 19175 |
| test_provincial | 201 |
| excluded_unknown_site | 2263 |

**Caveat (per CLAUDE.md open question 3, restated):** test_provincial = 201 documents total -- a small held-out set. Report this generalization experiment's results with wide uncertainty framing; do not oversell precision on a test set this size.

## Composition size-band distribution (stratification input)

| size_band | compositions |
|---|---|
| 1 | 122 |
| 2-5 | 194 |
| 21-50 | 94 |
| 51+ | 65 |
| 6-20 | 182 |

## Genre-band distribution (CTH//100, coarse proxy only)

| genre_band | compositions | docs |
|---|---|---|
| 0 | 65 | 450 |
| 100 | 72 | 434 |
| 200 | 83 | 1759 |
| 300 | 79 | 960 |
| 400 | 87 | 3062 |
| 500 | 70 | 2806 |
| 600 | 82 | 5705 |
| 700 | 87 | 2383 |
| 800 | 32 | 4080 |

*Full per-document assignment in splits.parquet.*