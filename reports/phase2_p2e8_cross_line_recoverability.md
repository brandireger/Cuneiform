# Phase 2 P2-E8 — cross-line witness recoverability census

**This is a census, not a calibration.** It establishes whether cross-line anchors have recoverable witness support at all. No number here is a probability, and none may be applied to a real gap as a rate — that requires the fold-structured step P2-E4/P2-E6 perform for same-line spans, which does not yet exist for cross-line.

## Why cross-line needs its own measurement

Every existing calibration was fit on masks generated strictly within a line. Cross-line anchors are **89.9% of anchored real gaps** (`reports/phase4_p4g_rerun.md`) and have never been measured. Borrowing a same-line rate for them would apply an estimate to a population it was never computed on.

## Boundaries refused rather than crossed

**9,582** of 23,090 adjacent line boundaries (41.5%) were not crossed because a neighbouring line renders empty under the language scope. Crossing one would fabricate adjacency between lines that have out-of-scope material between them — the fabrication `EXCLUDE_LINE` exists to prevent.

## Recoverability by cell, under both witness-admission rules

| cell | eligible | STRICT supported | STRICT incl. gold | LAYOUT_AGNOSTIC supported | LA incl. gold |
|---|---:|---:|---:|---:|---:|
| `a1_m1` | 25,178 | 18,308 (72.71%) | 3,432 (13.63%) | 19,660 (78.08%) | 5,378 (21.36%) |
| `a1_m2` | 35,708 | 25,872 (72.45%) | 2,522 (7.06%) | 27,823 (77.92%) | 4,225 (11.83%) |
| `a1_m3` | 44,544 | 32,171 (72.22%) | 1,904 (4.27%) | 34,539 (77.54%) | 3,210 (7.21%) |
| `a1_m5` | 57,053 | 40,628 (71.21%) | 1,448 (2.54%) | 43,759 (76.7%) | 2,222 (3.89%) |
| `a2_m1` | 44,544 | 6,540 (14.68%) | 1,904 (4.27%) | 8,352 (18.75%) | 3,210 (7.21%) |
| `a2_m2` | 51,666 | 7,967 (15.42%) | 1,631 (3.16%) | 9,774 (18.92%) | 2,641 (5.11%) |
| `a2_m3` | 57,053 | 9,289 (16.28%) | 1,448 (2.54%) | 11,148 (19.54%) | 2,222 (3.89%) |
| `a2_m5` | 62,873 | 10,465 (16.64%) | 1,183 (1.88%) | 12,212 (19.42%) | 1,570 (2.5%) |
| `a3_m1` | 57,053 | 3,312 (5.81%) | 1,448 (2.54%) | 4,314 (7.56%) | 2,222 (3.89%) |
| `a3_m2` | 60,787 | 3,923 (6.45%) | 1,325 (2.18%) | 4,804 (7.9%) | 1,875 (3.08%) |
| `a3_m3` | 62,873 | 4,376 (6.96%) | 1,183 (1.88%) | 5,113 (8.13%) | 1,570 (2.5%) |
| `a3_m5` | 63,308 | 4,587 (7.25%) | 881 (1.39%) | 5,111 (8.07%) | 1,059 (1.67%) |

## The finding: cross-line evidence is several times weaker

Gold inclusion, cross-line versus the same cell measured on same-line spans by the P4-D-corrected P2-E rerun:

| cell | same-line incl. gold | cross-line STRICT | cross-line LA | same-line ÷ STRICT |
|---|---:|---:|---:|---:|
| `a1_m1` | 47.75% | 13.63% | 21.36% | 3.5× |
| `a1_m2` | 31.33% | 7.06% | 11.83% | 4.4× |
| `a1_m3` | 20.94% | 4.27% | 7.21% | 4.9× |
| `a1_m5` | 9.7% | 2.54% | 3.89% | 3.8× |
| `a2_m1` | 20.94% | 4.27% | 7.21% | 4.9× |
| `a2_m2` | 14.24% | 3.16% | 5.11% | 4.5× |
| `a2_m3` | 9.7% | 2.54% | 3.89% | 3.8× |

**This is the empirical justification for the standing refusal to borrow a same-line rate for a cross-line anchor.** At `a2_m1` — the cell the real-gap single-sign calibration actually uses — same-line spans include the true reading in 20.94% of eligible cases and cross-line spans in 4.27%. Applying the same-line rate to a cross-line gap would have overstated the evidence by roughly a factor of five, on 89.9% of anchored real gaps. The prohibition was adopted on principle before it was measured; it now has a number.

`LAYOUT_AGNOSTIC` is a strict superset of `STRICT`: it admits same-line witness occurrences of the same anchor pair, on the ground that line division is scribal layout rather than textual structure. The gap between the two columns is the extra yield a reviewer should weigh before that rule is ratified.

## Where the line break falls (a2_m2, where every region is reachable)

| boundary region | eligible | STRICT incl. gold | LA incl. gold |
|---|---:|---:|---:|
| `in_mask` | 10,948 | 314 (2.87%) | 539 (4.92%) |
| `at_mask_start` | 10,543 | 310 (2.94%) | 511 (4.85%) |
| `at_mask_end` | 10,591 | 314 (2.96%) | 525 (4.96%) |
| `in_left_anchor` | 9,766 | 354 (3.62%) | 537 (5.5%) |
| `in_right_anchor` | 9,818 | 339 (3.45%) | 529 (5.39%) |

`in_mask` is the canonical cross-line case: the lost span itself straddles the line end, with a whole anchor on each line. `at_mask_start` / `at_mask_end` place the break flush against the mask, leaving both anchors intact. `in_left_anchor` / `in_right_anchor` split an anchor across the break — gaps sitting near a line edge whose anchor had to be walked across it, the situation `real_gap_witness_check.py` produces when it extends its anchor search up to 3 lines per side. For mask length 1, `in_mask` is unreachable by construction: a break cannot fall strictly inside one sign.

## Scope and limits

- Adjacent line pairs only (one boundary crossed). In the real-gap slice, 13,807 of 17,379 cross-line gaps crossed exactly one line; deeper crossings are a declared extension, not folded in silently.
- Dev split, attested-only, language scope `HITTITE_ONLY`, witness support required from an independent source family.
- No fold structure, so no rate here may be shown to an expert beside a candidate. That is the next step, and it is the step that would make cross-line real gaps presentable.

Runtime 11.4s · seed 20260727.
