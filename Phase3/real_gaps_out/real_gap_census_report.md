# Real-gap structural census (step 1)

<!-- p4d-staleness-stamp -->
> **[LANGUAGE-BLIND POPULATION — read with P4-D in mind]** This census counts
> real gaps without any language filter, which remains a correct description
> of the corpus. Downstream steps now scope queries explicitly (P4-D,
> 2026-07-26): on the witness-check slice ~9.5% of this population is
> non-Hittite or unresolved-language and is excluded from Hittite-only
> coverage figures. This report's own counts are unaffected and were not
> recomputed. See `reports/phase4_p4d_language_aware_apis.md`.

Pure structural count -- no witness lookup, no calibration, no UI.
Scope: train + dev documents only (bins and test excluded; test
exclusion checked via `lib.contracts.assert_no_test`, twice --
once on the allowed-ID set, once on what the decomposed reader
actually returned).

- **6,820** train/dev, non-bin documents in scope. **8** additional doc_id(s) excluded entirely for a real, pre-existing data problem this census surfaced: duplicate `splits.parquet` rows under different CTH numbers with disagreeing `main_split` values (one, `HT 39`, resolves to `test` under one interpretation) -- quarantined rather than guessed, matching `scripts/p2e_witness_recoverability.py`'s existing convention.
- **6,767** of those have at least one real gap (99.2%).
- **181,051** total real-gap runs found (133,351 pure `restored`, 38,881 pure `illegible_x`, 8,819 mixed within one contiguous run).

## Run length distribution (all real gaps, signs)

| length | count |
|---|---|
| 1 | 78,824 |
| 2 | 33,417 |
| 3 | 18,746 |
| 4 | 11,867 |
| 5 | 8,594 |
| 6 | 6,420 |
| 7 | 4,947 |
| 8 | 3,766 |
| 9 | 3,008 |
| 10 | 2,484 |
| 11 | 1,966 |
| 12 | 1,602 |
| 13 | 1,222 |
| 14 | 905 |
| 15 | 698 |
| 16 | 528 |
| 17 | 443 |
| 18 | 332 |
| 19 | 272 |
| 20 | 211 |
| 21 | 196 |
| 22 | 163 |
| 23 | 127 |
| 24 | 95 |
| 25 | 52 |
| 26 | 52 |
| 27 | 32 |
| 28 | 26 |
| 29 | 10 |
| 30 | 15 |
| 31 | 6 |
| 32 | 3 |
| 33 | 4 |
| 34 | 1 |
| 35 | 6 |
| 36 | 2 |
| 37 | 2 |
| 38 | 3 |
| 39 | 1 |
| 40 | 1 |
| 41 | 1 |
| 48 | 1 |

## Restored-run editor content (not yet compared to anything)

Of 133,351 pure-`restored` runs, **0** have no non-blank editor content at all (a restoration placeholder with nothing proposed).

| length | count |
|---|---|
| 1 | 46,650 |
| 2 | 25,468 |
| 3 | 16,016 |
| 4 | 10,551 |
| 5 | 7,754 |
| 6 | 5,824 |
| 7 | 4,407 |
| 8 | 3,418 |
| 9 | 2,743 |
| 10 | 2,261 |
| 11 | 1,795 |
| 12 | 1,465 |
| 13 | 1,117 |
| 14 | 833 |
| 15 | 639 |
| 16 | 488 |
| 17 | 414 |
| 18 | 307 |
| 19 | 257 |
| 20 | 197 |
| 21 | 184 |
| 22 | 150 |
| 23 | 117 |
| 24 | 89 |
| 25 | 50 |
| 26 | 49 |
| 27 | 31 |
| 28 | 24 |
| 29 | 9 |
| 30 | 15 |
| 31 | 6 |
| 32 | 2 |
| 33 | 4 |
| 34 | 1 |
| 35 | 5 |
| 36 | 2 |
| 37 | 2 |
| 38 | 3 |
| 39 | 1 |
| 40 | 1 |
| 41 | 1 |
| 48 | 1 |

## Top 15 compositions by real-gap count

| CTH | real-gap runs | documents in composition |
|---|---|---|
| 628 | 8,645 | 301 |
| 627 | 5,704 | 188 |
| 701 | 4,523 | 164 |
| 577 | 4,276 | 93 |
| 647 | 2,526 | 121 |
| 573 | 2,392 | 111 |
| 777 | 2,328 | 38 |
| 450 | 2,259 | 76 |
| 591 | 2,193 | 74 |
| 528 | 2,062 | 132 |
| 666 | 2,036 | 118 |
| 572 | 1,883 | 126 |
| 705 | 1,861 | 95 |
| 40 | 1,847 | 77 |
| 578 | 1,691 | 69 |

## What this does not yet tell us

Whether any independent witness exists for any of these gaps at all (step 2: build the anchor-context witness index and query it), or whether the editor's restored content agrees with what witnesses independently attest (step 3, restored spans only, per Ixca's "let the artifacts do the talking" framing). This step only establishes there is a real, sizeable population to build that layer for.