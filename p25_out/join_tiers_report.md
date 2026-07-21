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
