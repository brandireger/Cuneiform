# Phase 5 — the empty-middle census

**Status:** measured 2026-07-30. Closes the *measurement* half of
`PHASE5_SUCCESSOR_HANDOFF.md` open item 4. **The decision half is Ixca's and
this work deliberately stops short of it.** Nothing in the real-gap pipeline
was changed.

Artifacts: `scripts/real_gap_empty_middle_census.py`,
`Phase3/real_gaps_out/real_gap_empty_middle_census_report.md`,
`Phase3/real_gaps_out/real_gap_empty_middle_census.json`,
`tests/test_real_gap_empty_middle_census.py` (13 tests).

## What was being asked

Both index builders iterate `for middle_length in range(MAX_WITNESS_MIDDLE + 1)`,
so `middle_length == 0` is indexed like any other length: a witness in which
the query's two anchors stand **directly adjacent**, with nothing between.

For a single-sign gap that is not a reading. The query's own damage markup
asserts a sign stood there; a witness showing no sign contradicts the query's
structure. Presented to a specialist as a ranked candidate with a calibrated
rate beside it, it reads as *"the missing sign is: nothing"* — a claim the
calibration never measured.

Verified rather than assumed: observed gold lengths in this population are
`{1: 703}`. **The empty middle can be ranked but can never be correct.**

## Incidence

| | same-line | cross-line |
|---|---:|---:|
| eligible gaps | 703 | 46,118 |
| with any witness alternative | 160 (22.8%) | 5,676 (12.3%) |
| selector-accepted | 41 | 577 |
| empty middle present among alternatives | 32 | 1,081 |
| empty middle at rank 1 | 22 | 840 |
| **accepted AND empty middle at rank 1** | **1 (2.4%)** | **109 (18.9%)** |

The bolded row is the operative number. **This is overwhelmingly a cross-line
problem: nearly one in five accepted cross-line gaps would show a specialist
"nothing" as the best-supported proposal.** Same-line is a single case.

That asymmetry is not surprising in hindsight — cross-line anchors straddle a
line boundary, and line ends are exactly where a witness may legitimately have
the two anchors adjacent with no intervening sign.

## The finding that decides which remedy is coherent

When the pipeline accepts a gap whose top proposal is the empty middle, how
much other evidence is on the table?

| alternatives in the ranking | same-line | cross-line |
|---|---:|---:|
| 1 (the empty middle alone) | 1 | 79 |
| 2 | 0 | 21 |
| 3 | 0 | 5 |
| 4+ | 0 | 4 |

In **79 of 109** cross-line cases the empty middle is the *only* alternative.
It is not crowding a real reading out of rank 1 — it **is** the entire case,
and removing it leaves nothing.

In the remaining 30, other alternatives exist but none satisfies the fold's
acceptance rule once the empty middle is removed. That is why the
counterfactual records **zero** rank-1 changes and converts *every* one of the
109 into an abstention.

**Filtering does not surface a better reading here. It surfaces an
abstention.** That reframes the item: it is not a bug quietly degrading answer
quality, it is a population of gaps where the only witness evidence available
happens to contradict the query's structure.

## Counterfactual — reported to size the decision, not as a proposal

| | same-line | cross-line |
|---|---:|---:|
| accepted → rejected | 1 | 109 |
| rejected → accepted | 3 | 49 |
| accepted, rank-1 proposal changes | 0 | 0 |
| no alternative left at all | 9 | 311 |

**Net accepted gaps:** same-line 41 → 43, cross-line 577 → 517.

The `rejected → accepted` row is not noise: removing the empty middle can lift
a gap over the dominance and margin thresholds it was diluting. A filter would
therefore trade a set of confidently-wrong top candidates for a smaller set of
newly-admitted real ones. Whether that trade is good is what a refit would
have to measure, and this census cannot answer it.

Adopting a filter *because* this table looks better would report a search as a
measurement. It is reported so the decision can be sized, and for no other
reason.

## Why filtering is not free

The empty middle was in the anchor index when **P2-E4 and P2-E9 were fit** —
identical `build_anchor_index` / `build_cross_line_index`, identical
`MAX_WITNESS_MIDDLE`. It consumed rank positions during calibration exactly as
it does during application. Therefore:

1. **The ratified rates already price it in.** They are not inflated by its
   presence; if anything it depressed measured agreement, since it can occupy
   a rank the true reading would otherwise hold.
2. **Removing it at application time only would decouple the rate from the
   thing it rates.** The applied ranking would be a different construction
   from the calibrated one — the standing *do not use a second ranking
   implementation* prohibition, and how E2 happened.

Any filter must ship **with a refit**. That is a P2-E-shaped job, not a patch.

This is also why the counterfactual is computed by building a filtered *index
view* and passing it to the real `p2e2.proposal_ranking` /
`p2e9.merged_ranking`, rather than by post-processing a ranking. Five tests
pin that the view feeds those functions unchanged, including that the query's
own family is still excluded after filtering.

## The decision left open for Ixca

Three coherent options, ascending cost:

1. **Leave it.** Honest, and the calibration is sound. Costs a specialist an
   occasional visibly-wrong top candidate — about one in five accepted
   cross-line gaps.
2. **Display-layer treatment.** Keep the empty middle in the ranking, so the
   calibration still matches what is applied, but render it as what it is —
   *witnesses attest these anchors adjacent; this contradicts the query's
   damage markup* — rather than as a reading. No refit needed, because the
   ranking is unchanged. This is also the option most consistent with the
   project's output contract, which already requires typed contradictory
   evidence and an explicit residual option.
3. **Filter and refit.** Rebuild P2-E4 and P2-E9 with the empty middle
   excluded, and re-derive every downstream rate. Cleanest, most expensive,
   and it changes ratified numbers.

**Option 2 is where I would start** — it is the only one that neither ships a
misleading candidate nor touches a ratified artifact. But it is a scoring/
display policy decision, and the census stops here rather than making it.

## Validation

```powershell
python scripts/real_gap_empty_middle_census.py
python -m unittest tests.test_real_gap_empty_middle_census   # 13 pass
python -m unittest discover -s tests                          # 246 pass
ruff check lib scripts tests demo                             # clean
python lib/contracts.py                                       # 20/20
python scripts/p4d_stamp_stale_reports.py --check             # exit 0
```

Eligible populations reproduce the handoff exactly (703 same-line eligible /
41 accepted; 46,118 cross-line eligible / 577 accepted), which is the check
that the census walked the same population production does.
