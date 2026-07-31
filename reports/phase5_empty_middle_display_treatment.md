# Phase 5 — empty-middle display treatment (option 2, adopted)

**Status:** implemented 2026-07-30. **Not browser-verified** — see "What is
not verified". Follows `reports/phase5_empty_middle_census.md`, which measured
the problem; Ixca chose **option 2 (display-layer treatment)** after reviewing
five worked examples.

## What was adopted, and what was explicitly not

The empty middle **keeps its rank and its witness support**. Nothing is
filtered, reordered, or reweighted. That is the whole point: the empty middle
was in the anchor index when P2-E4 and P2-E9 were *fit*, so the ratified rates
already price it in, and removing it at application time only would decouple
the rate from the thing it rates — the standing *do not use a second ranking
implementation* prohibition.

What changed is how it is **presented**:

| before | after |
|---|---|
| a candidate card with a blank sign line | labelled `(no sign)`, marked **not a reading**, warning-bordered |
| captioned "a witnessed omission, not missing data" | branch-specific text saying what the witnesses actually establish |
| carried the rank-1 group rate (~78%) | rate **withheld** with an explicit reason |
| no contradictory evidence emitted | typed `WITNESS_ANCHORS_ADJACENT` / `CONTRADICTS_QUERY_STRUCTURE` |
| no limitation | `EMPTY_MIDDLE_CONTRADICTS_QUERY_STRUCTURE` on the packet |
| "Select this option" | "Record that no sign stood here (disputes the markup)" |

**Why the rate is withheld.** The rank-level estimand is *"the fraction whose
hidden/true attested middle occurs at that rank"*. An option proposing no
signs cannot be an attested middle, so it is not in that estimand's support.
Printing 78% beside it invites the reader to treat a rank-level track record
as this option's chance of being right, when it is definitionally 0.

**The old caption was worse than neutral.** "A witnessed omission, not missing
data" asserts that the omission is real. The witnesses do not establish that —
they contradict the query's own assertion that a sign stands there. That is a
different and much weaker claim.

## Four branches, because these are four different situations

`classify_empty_middle()` fails closed on an unknown kind. There is no
default: "witnesses show nothing here" means something different in each case,
and collapsing them into one sentence is the defect being replaced.

| kind | what it means | real-gap share |
|---|---|---:|
| `ILLEGIBLE_TRACE` | editor saw a trace, could not read it → *your trace is off-formula* | 57 of 109 |
| `EDITORIAL_RESTORATION` | editor proposed a sign → **the witnesses contradict a scholarly bracket** | 41 of 109 |
| `INDETERMINATE_LACUNA` | editor marked `…` → *the parallel tradition has no gap here* | 11 of 109 |
| `HIDDEN_ATTESTED_SIGN` | synthetic evaluation context → cannot be correct by construction | evaluation only |

The `EDITORIAL_RESTORATION` branch is the one worth the most. It is the system
automatically surfacing places where a scholar's restoration disagrees with
the manuscript tradition — cleanroom rules 3 and 6 in operation, previously
disguised as a display bug.

`empty_middle_query_kind_for_damage()` maps a real gap's encoded
`damage_state` onto these, with the ellipsis token overriding its own
`restored` state — an indeterminate lacuna is tagged `restored`, but the
editor proposed no sign, and calling it a restoration would misreport what
they wrote.

## Scope correction found during implementation

My earlier count of "5 of 16 P2-E4 packets" was **under-reported**. It read
`candidate_set.alternatives`, but P2-E6 stores its options under
`tie_complete_alternatives`. The real figure across the exported demo set is
**10 empty-middle options in 28 packets**: 5 single-sign and 5 multi-sign,
including `p2e6-002` at rank 1 on **19 independent families**.

So the multi-sign path was affected too and is now covered. There the withheld
rate is the set-inclusion rate, on the same grounds.

## Changes

| file | change |
|---|---|
| `lib/expert_decision_contract.py` | `EMPTY_MIDDLE_QUERY_KINDS`, `classify_empty_middle()`, `annotate_empty_middle_options()`, `is_empty_middle_option()`, `empty_middle_query_kind_for_damage()`, `_validate_option_display()`; wired into both adapters |
| `demo/taksan_missing_text_prototype.html` | option card, preview dropdown, select-button label, CSS; added `escapeHtml()` (the page had none) |
| `scripts/real_gap_calibration.py` | replaced the now-stale "left as-is, needs its own justification" paragraph with the measured result and the adopted remedy |
| `tests/test_expert_decision_contract.py` | +14 tests |
| `tests/test_taksan_empty_middle_render.py` | new, 9 tests |

**The schema is two-sided.** An option proposing no signs is *required* to
carry a display block, and a display block on an option that proposes signs is
rejected. The defect being fixed fails silently — a renderer just draws an
empty card — so the schema has to catch it rather than relying on callers.

## Deliberately left alone

- **`CONTRACT_VERSION` stays 1.1.0.** The additions are additive, but a
  renderer written against 1.1.0 that ignores `display` would draw an empty
  candidate — the exact defect. Only one renderer exists and it is updated
  here, and the schema now refuses to emit an unannotated empty option. If
  Ixca wants the `display` block to be a hard renderer requirement rather than
  a producer-side invariant, that is a version bump needing ratification.
- **The empty middle stays selectable.** An expert concluding that no sign
  stood there — that the markup is wrong — is a legitimate judgment. Removing
  the action would change `workflow.allowed_actions`, which is contract
  behavior, not display. Only the label changed. Whether it should remain
  selectable is a reasonable follow-up question.
- **No ranking, calibration, or ratified artifact was touched.** Real-gap
  eligible/accepted counts are unchanged: 703/41 same-line, 46,118/577
  cross-line.

## What is not verified

**No browser render check.** No browser tool was available. Verification was
an esprima parse of the page script, HTML tag-nesting validation, and the test
suite. **The Takšan prototype needs a smoke test before expert use** — the
option card, preview dropdown, and select button all changed, and this page
has never had a recorded browser smoke test at all (unlike the workbench).
This is now the second page awaiting one.

**No specialist has assessed the wording.** The four branch texts are my
reading of what the witnesses establish in each case. They are the sentences a
Hittitologist will actually read, and they should be reviewed as copy, not
just as logic.

## Two open items surfaced by this work, not folded into it

1. **`…` indeterminate lacunae are being counted as single-sign gaps** —
   2,725 of 46,118 cross-line eligible, and 35,221 restored ellipsis tokens
   corpus-wide. A `…` is "an unknown amount is missing", not one sign, so
   arguably these do not belong in a single-sign population at all. That is a
   scope question for the real-gap pipeline and should not be settled as a
   side effect of a display change.
2. **`AT 454` is filed under CTH 577** and reads as a Hittite oracle report,
   but `AT` is CLAUDE.md's Alalakh siglum with exactly one document. Worth
   checking whether the site-prefix table is mis-assigning it — it bears on
   the Hattusa→provincial generalization experiment.

## Validation

```powershell
python -m unittest discover -s tests                  # 274 pass (was 246)
ruff check lib scripts tests demo                     # clean
python lib/contracts.py                               # 20/20
python scripts/00_tracers.py                          # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check     # exit 0
git diff --check                                      # clean
```

Rebuild:

```powershell
python scripts/p2e7_contract_check.py
python demo/dm1_missing_text_export.py
python scripts/real_gap_calibration.py
```
