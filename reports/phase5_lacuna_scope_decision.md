# Phase 5 — indeterminate-lacuna scope decision

**Status: RATIFIED 2026-07-31 (split estimand); IMPLEMENTED AND VERIFIED
2026-08-01.** Closes handoff item 5a. This memo drafted both options and their
measured downstream effects; the decision is recorded at the bottom. No
protected-test access, model, or training is involved; this is a
population-composition question, not a calibration-quality one.

## The question

An indeterminate-lacuna token `…` means **"an unknown amount of text is
missing here"** — not "one sign is missing." It currently enters the
**single-sign** real-gap population anyway, because its encoded `damage_state`
is `restored` and the single-sign scope admits `restored` positions. The
empty-middle work surfaced this as a side effect and deliberately did **not**
settle it there, because it moves a headline population count.

## The measured facts (from the census, not estimated)

| quantity | value | source |
|---|---:|---|
| `…` tokens inside cross-line **single-sign eligible** | **2,725** | `real_gap_empty_middle_census.json` |
| cross-line single-sign eligible (total) | 46,118 | `real_gap_calibration.json` |
| `…` as a share of cross-line eligible | **5.9%** | derived |
| restored `…` tokens corpus-wide | 35,221 | census |
| cross-line **accepted** gaps (current) | 577 | calibration.json |
| accepted gaps where an empty middle sits at **rank 1** | 109 | census |
| of those, empty middle is the **sole** alternative | 79 | census |
| of those 109, classified `INDETERMINATE_LACUNA` | 11 | display-treatment report |

The last row is the one that matters for scope: only **11** of the 109
rank-1 empty-middle acceptances are ellipsis-driven. The other 98 are
`ILLEGIBLE_TRACE` (57) or `EDITORIAL_RESTORATION` (41) — real damage states,
not indeterminate lacunae, and unaffected by whichever option is chosen.

## Option A — exclude `…` from the single-sign population

Treat an indeterminate lacuna as categorically ineligible for a single-sign
gap, because a `…` does not assert that exactly one sign is missing. Filter it
at `prepare_scope()`, before eligibility, symmetric with the language filter.

- **Cross-line eligible:** 46,118 → **43,393** (−2,725, −5.9%).
- **Accepted:** at most −11 (the `INDETERMINATE_LACUNA` rank-1 acceptances);
  likely fewer once re-ranked, since removing an ellipsis option can promote a
  real reading rather than drop the gap. Same-line accepted (41) is unaffected —
  the census shows zero same-line `INDETERMINATE_LACUNA` acceptances.
- **What it buys:** the single-sign population then means what it says. Every
  accepted single-sign gap is a place where exactly one sign is claimed
  missing, and no coverage number is inflated by "unknown-length" positions.
- **What it costs:** a real drop in the eligible denominator (though the
  *accepted* headline barely moves), and a new filter that must be justified
  and tested. The `…` positions do not disappear — they become candidates for
  a future variable-length gap track, which does not exist yet.

## Option B — keep `…`, document the caveat

Leave the population as built; add a typed caveat that indeterminate lacunae
are present in the single-sign eligible set and are handled at display time by
the adopted empty-middle treatment (labelled `(no sign)`, rate withheld).

- **Cross-line eligible:** 46,118 (unchanged). **Accepted:** 577 (unchanged).
- **What it buys:** no recomputation, no new filter, and the empty-middle
  display treatment already prevents an ellipsis from being *shown* as a
  confident one-sign reading — so the user-facing risk is already contained.
- **What it costs:** the single-sign population contains 2,725 positions that
  are not honestly single-sign. Any paper sentence of the form "N single-sign
  gaps" is then true only with an asterisk, and a reader auditing the
  denominator will find the asterisk. The caveat lives in prose, not in the
  data's own scope label.

## The honest asymmetry, stated plainly

The **accepted** headline is nearly identical either way (≤11 gaps move), so
this is not a fight over coverage. It is a fight over what the **denominator**
*means*. Option A makes the population definition literally true at the cost of
a rerun and a filter. Option B keeps the numbers frozen at the cost of a
standing caveat on every "single-sign" claim. Neither is a bug fix; the census
number is correct under both. Pick the one whose cost you would rather defend
in the paper's methods section.

A third path exists and is worth naming so it is not silently chosen: **split
the estimand** — report single-sign coverage twice, once on the full eligible
set and once on the ellipsis-excluded subset, and let the gap between them be a
disclosed figure. That costs a column, not a rerun, and it is the most
defensible if you are undecided, because it shows the reader exactly what the
2,725 positions do to the numbers instead of asserting they do nothing.

## Decision

> **Ratified by: Ixca  Date: 2026-07-31**
> **Choice: split — report the estimand twice.**
> Single-sign coverage is reported on the full eligible set (46,118) and on the
> ellipsis-excluded subset (43,393), with the gap between them disclosed as a
> figure. No positions are filtered from calibration; the split is a reporting
> layer, so no accepted-gap count changes and no ratified rate is disturbed. The
> 2,725 indeterminate lacunae stay in the fitted population and are handled at
> display time by the adopted empty-middle treatment; the second denominator
> exists so a reader can see exactly what they contribute rather than take it on
> faith.

**Implemented and verified 2026-08-01.** The full derived-data chain (raw
TLHdig 0.2.0-beta corpus, MD5-verified against the pin; the archived P1/P2.5
pipeline; the P4-D language-layer artifacts) was rebuilt from scratch in a
fresh environment, since none of it is checked into git by design. Before
touching anything, the *unmodified* `real_gap_calibration.py` was run against
the rebuilt data and reproduced the already-committed 46,118/577 figures
exactly, including a byte-identical `language_dataset_file_sha256` — proof the
rebuild is faithful, not just plausible. `real_gap_calibration.py` was then
extended with `exclude_indeterminate_lacunae()` and rerun: it reports
**43,393** ellipsis-excluded against the **46,118** full eligible population,
an implied **2,725** indeterminate-lacuna count — exactly matching this
memo's figures. `real_gap_calibration.json` and its report now carry both
denominators, and `tests/test_real_gap_calibration_scope.py` pins the new
function alongside the existing union-scope tests. No position was filtered
from calibration; no accepted-gap count or ratified rate changed.
