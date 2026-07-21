# P2.5 A3 -- Join Tiers Report

- Total pairs: 1581

## Tier counts

| tier | geometry | count |
|---|---|---|
| A | vertical | 478 |
| B | vertical | 185 |
| C | horizontal | 918 |

## Tier x join_type

| tier | join_type | count |
|---|---|---|
| A | direct | 313 |
| A | indirect | 165 |
| B | direct | 97 |
| B | indirect | 2 |
| B | inferred_from_shared_lines | 86 |
| C | None | 1 |
| C | direct | 558 |
| C | indirect | 46 |
| C | inferred_from_shared_lines | 313 |

## Tier x parent_is_bin

| tier | parent_is_bin | count |
|---|---|---|
| A | False | 368 |
| A | True | 110 |
| B | False | 140 |
| B | True | 45 |
| C | False | 662 |
| C | True | 256 |

## n_shared_lines histogram

| n_shared_lines | count |
|---|---|
| 0 | 478 |
| 1 | 94 |
| 2 | 91 |
| 3 | 100 |
| 4 | 83 |
| 5 | 95 |
| 6 | 72 |
| 7 | 109 |
| 8 | 80 |
| 9 | 59 |
| 10 | 67 |
| 11 | 50 |
| 12 | 30 |
| 13 | 31 |
| 14 | 19 |
| 15 | 22 |
| 16 | 13 |
| 17 | 10 |
| 18 | 11 |
| 19 | 9 |
| 20 | 6 |
| 21 | 4 |
| 22 | 7 |
| 23 | 8 |
| 24 | 2 |
| 25 | 6 |
| 26 | 4 |
| 27 | 5 |
| 28 | 1 |
| 29 | 3 |
| 30 | 1 |
| 31 | 1 |
| 32 | 1 |
| 33 | 1 |
| 35 | 2 |
| 36 | 1 |
| 37 | 1 |
| 40 | 1 |
| 43 | 1 |
| 44 | 1 |
| 61 | 1 |

## Tier-C exclusive-content variant
- Tier-C pairs: 918
- exclusive_untestable (< 8 attested signs or < 2 lines remaining after shared-line deletion in EITHER member): 487 (53.1% of tier-C, if tier-C > 0)

**Evaluation policy (for the eval harness in a later phase): tier A is the headline physical-join metric; tier B secondary; tier C is reported ONLY via the exclusive-content variant as the honest number (excluding exclusive_untestable pairs), with the full-reconstruction number shown alongside labeled as an upper bound (it is contaminated by shared-line duplication).**

## Worked examples (one per tier)

### Tier A -- KBo 53.33+ (KUB 48.76 <-> CHDS 3.51)
- join_type: direct, n_shared_lines: 0, parent_is_bin: False

### Tier B -- KBo 33.10+ (KBo 19.124 <-> KBo 54.5)
- join_type: direct, n_shared_lines: 2, parent_is_bin: False

### Tier C -- KBo 53.33+ (KBo 6.34 <-> KUB 48.76)
- join_type: direct, n_shared_lines: 11, parent_is_bin: False
- member_a exclusive ATTESTED (149 lines, 1873 signs): x-zi / li-in-ki-ia / zi nu te-ez-zi
- member_b exclusive ATTESTED (8 lines, 53 signs): QA-TI-ŠU-NU da-a-i / ia-an-zi nu e-ek-ta-an / aš-nu-zi nu-uš-ma-aš te-ez-zi

## Tier-C exclusive-content spot-check (3 pairs, acceptance check 4)

Seeded random sample (seed=20260721) from 431 testable tier-C pairs, showing full reconstruction (contaminated by the shared overlap) vs. exclusive-content rendering (shared lines removed) side by side, to make visible exactly what the exclusive variant strips out.

### Spot-check 1/3 -- KBo 43.44+ (KBo 43.44 <-> KBo 24.62)
- n_shared_lines: 5, join_type: direct, parent_is_bin: True
- member_a FULL (5 exclusive + 5 shared lines total): x A-NA / ši-pa-an-ti na-aš / EGIR-ŠU-ma la-aḫ / na-aš-kán ta-pu-ú-ša
- member_a EXCLUSIVE ATTESTED (5 lines, 10 signs, shared lines removed): x A-NA / ti na-aš / ŠU-ma la-aḫ
- member_b FULL: I-NAÉ D10 ta-pu-ú-ša zé-an-da-az / nu A-NAD10 UD-aš NINDAga-ag-ga-ri-uš pár-ši-ia / 5 NINDA.SIG-ma A-NADta-aš-mi-šu pár-ši-ia x / EGIR-ŠU-ma la-ḫa-an-ni-uš ši-pa-an-ti 5 NINDA.SIG
- member_b EXCLUSIVE ATTESTED (10 lines, 26 signs): D10 ta-pu-ú-ša zé-an-da-az / x / x / ta GAL Dḫé-pát šu-un-na-an-zi

### Spot-check 2/3 -- KBo 25.12+ (ABoT 1.5 <-> KBo 17.9)
- n_shared_lines: 8, join_type: inferred_from_shared_lines, parent_is_bin: False
- member_a FULL (24 exclusive + 8 shared lines total): LÚMEŠ˽GIŠ.DINANNAḪI.A ka-ni-iš SÌR-RU / LUGAL-uš MUNUS.LUGAL-aš-ša TUŠ-aš Dḫu-ul-la-a-an a-ku-an-zi / LÚ.MEŠGI.GÍD SÌR-RU 10 NINDAḪI.A 2 ḫu-up-pár KAŠ.GEŠTIN A-NALÚ.MEŠGI.GÍD pí-an-zi / LUGAL-uš MUNUS.LUGAL-aš-ša TUŠ-aš Dte-li-pí-nu-un a-ku-an-zi
- member_a EXCLUSIVE ATTESTED (24 lines, 160 signs, shared lines removed): ka-ni SÌR-RU / LUGAL-uš MUNUS.LUGAL-aš-ša TUŠ-aš Dḫu-ul-la-a-an a-ku / LÚ.MEŠGI.GÍD SÌR-RU 10 NINDAḪI.A 2 ḫu-up-pár KAŠ.GEŠTIN / LUGAL-uš MUNUS.LUGAL-aš-ša TUŠ-aš Dte-li-pí-nu
- member_b FULL: GIŠ.DINANNA TUR Ú-UL / a-aš-ki 2 e-ku-zi / zi GIŠ.DINANNA TUR LÚ.MEŠḫal-li-ri-eš SÌR-RU / ta a-ri 1 e-ku-zi
- member_b EXCLUSIVE ATTESTED (23 lines, 116 signs): TUR Ú-UL / a-aš-ki 2 e-ku / GIŠ.DINANNA TUR LÚ.MEŠḫal-li-ri / a-ri 1 e-ku-zi

### Spot-check 3/3 -- KBo 29.65+ (KBo 29.65 <-> KBo 41.12)
- n_shared_lines: 5, join_type: direct, parent_is_bin: True
- member_a FULL (52 exclusive + 5 shared lines total): nu 3 / zi ŠÀ.BA x / DUGšu-ú-wa-at-raḪI.A ti / ku-it-ta ŠA1 PA-RI-SI
- member_a EXCLUSIVE ATTESTED (52 lines, 714 signs, shared lines removed): nu 3 / ŠÀ.BA x / ú-wa-at-raḪI.A ti / ta ŠA1 PA-RI-SI
- member_b FULL: na-at x / i-mi-e-zi / ŠA DUGšu / NINDAḪI.A-ma x
- member_b EXCLUSIVE ATTESTED (19 lines, 50 signs): na-at x / i-mi-e-zi / ŠA DUGšu / NINDAḪI.A-ma x
