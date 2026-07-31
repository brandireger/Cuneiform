# Real gaps — empty-middle census

**This is a census, not a scoring change.** Nothing in the real-gap pipeline was altered by running it. It closes the measurement half of `PHASE5_SUCCESSOR_HANDOFF.md` open item 4; the decision half is Ixca's.

## What the empty middle is

A witness proposal is whatever sits between the query's two anchors in an independent witness. Both index builders iterate `range(MAX_WITNESS_MIDDLE + 1)`, so `middle_length == 0` is indexed like any other length: a witness in which the two anchors are directly **adjacent**.

For these single-sign gaps (mask length 1) that proposal cannot be a reading. The query's damage markup asserts a sign stood there; a witness showing no sign disagrees with the query's structure. Shown to a specialist as a ranked candidate with a calibrated rate beside it, it would read as *“the missing sign is: nothing”* — a different claim from anything the calibration measured.

Verified rather than assumed: observed gold lengths in this population are `{1: 703}`, so a zero-length gold does not occur. The empty middle can be **ranked** but never **correct**.

## Incidence

| | same-line | cross-line |
|---|---:|---:|
| eligible gaps | 703 | 46,118 |
| with any witness alternative | 160 (22.8%) | 5,676 (12.3%) |
| selector-accepted | 41 (25.6%) | 577 (10.2%) |
| empty middle present among alternatives | 32 (20.0%) | 1,081 (19.0%) |
| empty middle at rank 1 | 22 (13.8%) | 840 (14.8%) |
| **accepted AND empty middle at rank 1** | 1 (2.4%) | 109 (18.9%) |

The bolded row is the operative number: gaps where the pipeline accepts, and the proposal a specialist would see first is *nothing*.

### Where the empty middle ranks, when present

| rank | same-line | cross-line |
|---|---:|---:|
| 1 | 22 | 840 |
| 2 | 6 | 184 |
| 3 | 4 | 25 |
| 4 | 0 | 20 |
| 5 | 0 | 6 |
| 6+ | 0 | 6 |

### When it is accepted at rank 1, what else is on the table?

| alternatives in the ranking | same-line | cross-line |
|---|---:|---:|
| 1 | 1 | 79 |
| 2 | 0 | 21 |
| 3 | 0 | 5 |
| 4+ | 0 | 4 |

**This is the finding that decides which remedy is coherent.** When the pipeline accepts a gap whose top proposal is the empty middle, the empty middle is the *only* alternative in 1 of 1 same-line and 79 of 109 cross-line cases. In those it is not crowding a real reading out of rank 1 — it **is** the entire case, and removing it leaves nothing.

In the remaining 30 cross-line cases other alternatives do exist, but none of them satisfies the fold's acceptance rule once the empty middle is removed — which is why the counterfactual below records **zero** rank-1 changes and turns *every* one of these accepts into an abstention. Filtering does not surface a better reading here. It surfaces an abstention.

## Counterfactual — what a filter would change

**This is not a proposal.** It sizes the decision. Adopting a filter because this table looks better would report a search as a measurement.

| | same-line | cross-line |
|---|---:|---:|
| accepted → rejected | 1 | 109 |
| rejected → accepted | 3 | 49 |
| accepted, rank-1 proposal changes | 0 | 0 |
| no alternative left at all | 9 | 311 |

**Net effect on accepted gaps:** same-line 41 → 43, cross-line 577 → 517.

The `rejected → accepted` row is the other side of the ledger and is not noise: removing the empty middle can lift a gap over the dominance and margin thresholds it was diluting. So a filter would not be purely subtractive — it would trade a set of confidently-wrong top candidates for a smaller set of newly-admitted real ones. Whether that trade is good is exactly what a refit would have to measure, and this census cannot answer it.

## Why filtering is not free

The empty middle was in the anchor index when **P2-E4 and P2-E9 were fit** — identical `build_anchor_index` / `build_cross_line_index`, identical `MAX_WITNESS_MIDDLE`. It consumed rank positions during calibration exactly as it does during application. So:

1. **The ratified rates already price it in.** They are not inflated by its presence; if anything it depressed measured agreement, because it can occupy a rank the true reading would otherwise hold.
2. **Removing it at application time only would decouple the rate from the thing it rates.** The applied ranking would be a different construction from the calibrated one — the standing *do not use a second ranking implementation* prohibition, and how E2 happened.

Any filter must therefore ship **with a refit**, not bolted onto the application step. That is a P2-E-shaped job, not a patch.

## The decision this leaves open

Three coherent options, in ascending cost:

1. **Leave it.** Honest, and the calibration is sound. Costs a specialist an occasional visibly-wrong top candidate.
2. **Display-layer treatment.** Keep the empty middle in the ranking (so the calibration still matches) but render it as what it is — *witnesses attest these anchors adjacent; this contradicts the query's damage markup* — rather than as a reading. No refit needed, because the ranking is unchanged.
3. **Filter and refit.** Rebuild P2-E4 and P2-E9 with the empty middle excluded from the index, and re-derive every downstream rate. Cleanest, most expensive, and it changes ratified numbers.

Option 2 is the one that does not require touching a ratified artifact, and it is where I would start — but it is Ixca's call, and this census deliberately stops short of making it.

## Examples — accepted, empty middle at rank 1 (same-line)

- `KBo 45.89`: empty middle supported by 2 independent family/families; runner-up `(none)` with 0; 1 alternative(s) total.
